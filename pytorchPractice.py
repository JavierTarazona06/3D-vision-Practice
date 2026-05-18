import __main__
from xml.parsers.expat import model

import torch
import torch.nn as nn

from models.SimpleNeuralNetworkModel import SimpleNeuralNetworkModel
from scripts.training_loop import training_loop


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

    print("===========================")
    print("# Simple Neural Network Model")
    print("===========================")
    myModel = SimpleNeuralNetworkModel()
    training_loop(myModel)

    return 0

if __name__ == "__main__":
    main()
