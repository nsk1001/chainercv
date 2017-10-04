from chainer import cuda
from chainer import optimizer


_default_hyperparam = optimizer.Hyperparameter()
_default_hyperparam.lr = 0.01
_default_hyperparam.momentum = 0.9


class CorrectedMomentumSGDRule(optimizer.UpdateRule):

    # use update rule used in frameworks like Torch.

    def __init__(self, parent_hyperparam=None, lr=None, momentum=None):
        super(CorrectedMomentumSGDRule, self).__init__(
            parent_hyperparam or _default_hyperparam)
        if lr is not None:
            self.hyperparam.lr = lr
        if momentum is not None:
            self.hyperparam.momentum = momentum

    def init_state(self, param):
        xp = cuda.get_array_module(param.data)
        with cuda.get_device_from_array(param.data):
            self.state['v'] = xp.zeros_like(param.data)

    def update_core_cpu(self, param):
        grad = param.grad
        if grad is None:
            return
        v = self.state['v']
        v *= self.hyperparam.momentum
        v -= self.hyperparam.lr * grad
        param.data += v

    def update_core_gpu(self, param):
        grad = param.grad
        if grad is None:
            return
        cuda.elementwise(
            'T grad, T lr, T momentum',
            'T param, T v',
            '''v = momentum * v - grad;
               param += lr * v;''',
            'momentum_sgd')(
                grad, self.hyperparam.lr, self.hyperparam.momentum,
                param.data, self.state['v'])


class CorrectedMomentumSGD(optimizer.GradientMethod):

    def __init__(self, lr=_default_hyperparam.lr,
                 momentum=_default_hyperparam.momentum):
        super(CorrectedMomentumSGD, self).__init__()
        self.hyperparam.lr = lr
        self.hyperparam.momentum = momentum

    lr = optimizer.HyperparameterProxy('lr')
    momentum = optimizer.HyperparameterProxy('momentum')

    def create_update_rule(self):
        return CorrectedMomentumSGDRule(self.hyperparam)
