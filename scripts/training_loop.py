import torch
import torch.nn as nn

from models.SimpleNeuralNetworkModel import SimpleNeuralNetworkModel

def training_loop(model: SimpleNeuralNetworkModel):
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Change Model to CPU
    # Loss Function, ideal for multi-class classification problems.
    # Optimizes model weights during trainning, using the Adam optimization algorithm.
    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    # Creates random tensor of 32 batch-size with 10 features each at GPU
    # Creates random target tensor (class labels) of 32 samples with values between 0 and 1
    inputs = torch.randn(32, 10).to(device)
    print("Input tensor:\n", inputs)
    targets = torch.randint(0, 2, (32,)).to(device)
    print("Target tensor:\n", targets)

    # Runs models forward pass, computes the loss, and updates the model weights using backpropagation.
        # For each example (rows), the columns are the score (logits) for each class (0 and 1 in this case).
    # Measure how bad predictions are, compared with targets and outputs logits
    # Input -> Output -> Loss
    outputs = model(inputs)
    print("Output tensor:\n", outputs)
    loss = criterion(outputs, targets)

    # Previous gradients must be zeroed to avoid gradients accumulation between iterations
    # For the current batch, computes the gradients of the loss with respect to the model parameters 
        # (weights and biases) using backpropagation.
    # Based on the gradients, applies Adam to update model weights to minimize the loss.
    # Loss -> Outpouts -> Model Parameters
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    # Backpropagation if taking the scalar loss and use the caculus
        # chain rule to propagate derivates backward though the network. Thats is
        # the model parameters, the weight and bias. For each neuron the gradient will
        # indicate how much the loss would change if the parameter were changed.
        # Then the optimizer use that information to update the parameters in a way that minimizes the loss.
    # Then the gradients can be expected as :
    print("Gradients of the model parameters - Weight:") # Get 2 neurons with 10 weigths each as parameter
    print(model.linear.weight.grad)
    print("Gradients of the model parameters - Bias:") # Get 2 neurons with their related bias parameters
    print(model.linear.bias.grad)

    # Gets the scalar value of loss tensor
    print("Loss value: ")
    print(loss.item())
