import __main__

import torch
import torch.nn as nn

class SimpleNeuralNetworkModel(nn.Module):
    """Simple neural network with one linear layer.
    Inherits from nn.Module, which is the base class for all neural network modules in PyTorch.

    This model maps an input vector of size 10 to an output vector of size 2.

    Args:
        input_dim: Number of input features.
        output_dim: Number of output features.
    """

    def __init__(self, input_dim: int = 10, output_dim: int = 2) -> None:
        super().__init__()
        self.linear = nn.Linear(input_dim, output_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Run the forward pass.
        How data passes and changed in the model.

        Args:
            x: Input tensor with shape [batch_size, input_dim].

        Returns:
            Output tensor with shape [batch_size, output_dim].
        """
        return self.linear(x)


def training_loop():

def main():
    
    print("===========================")
    print("# Tensors")
    print("===========================")
    x = torch.tensor([1.0, 2.0, 3.0])
    print("A tensor: ", x)

    print("===========================")
    print("# GPU Control")
    print("===========================")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    x = torch.tensor([1.0, 2.0, 3.0]).to(device)
    print("Device: ", device)
    print("Tensor on device: ", x)

    return 0

if __name__ == "__main__":
    main()