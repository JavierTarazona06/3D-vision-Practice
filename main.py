import __main__
from xml.parsers.expat import model

import torch

from models.SimpleNeuralNetworkModel import SimpleNeuralNetworkModel
from scripts.data_manager import main as data_manager_main
from scripts.training_loop import training_loop


def show_tensors() -> None:
    print("===========================")
    print("# Tensors")
    print("===========================")
    x = torch.tensor([1.0, 2.0, 3.0])
    print("A tensor: ", x)


def show_gpu_control() -> None:
    print("===========================")
    print("# GPU Control")
    print("===========================")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    x = torch.tensor([1.0, 2.0, 3.0]).to(device)
    print("Device: ", device)
    print("Tensor on device: ", x)


def run_simple_model() -> None:
    print("===========================")
    print("# Simple Neural Network Model")
    print("===========================")
    myModel = SimpleNeuralNetworkModel()
    training_loop(myModel)


def run_data_manager() -> None:
    print("===========================")
    print("# Data Manager")
    print("===========================")
    data_manager_main()


def main():
    while True:
        print("===========================")
        print("# Menu")
        print("===========================")
        print("0. Exit")
        print("1. Tensors")
        print("2. GPU Control")
        print("3. Simple Neural Network Model")
        print("4. Data Manager")

        choice = input("Select an option (0-4): ").strip()

        if choice == "0":
            break
        elif choice == "1":
            show_tensors()
        elif choice == "2":
            show_gpu_control()
        elif choice == "3":
            run_simple_model()
        elif choice == "4":
            run_data_manager()
        else:
            print("Invalid option.")

    return 0

if __name__ == "__main__":
    main()
