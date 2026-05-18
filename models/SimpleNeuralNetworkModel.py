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
        # Creates a linear layer that transforms input_dim features to output_dim features.
            # Using output = input @ weight.T + bias
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
