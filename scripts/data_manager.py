import torch

from torch.utils.data import Dataset, DataLoader


class MyDataset(Dataset):
    """Dataset example for supervised learning.
    
    args:
        data: List of tensors, teh input data for the model.
        labels: List of integers representing the corresponding labels for the data.
    """

    def __init__(self, data: list[torch.Tensor], labels: list[int]) -> None:
        self.data = data
        self.labels = labels

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        return self.data[index], self.labels[index]
    
    def __str__(self) -> str:
        return super().__str__() + f"\nData: {self.data}\nLabels: {self.labels}"

def main():
    dataset = MyDataset(
        data=[torch.randn(10) for _ in range(100)],
        labels=[0 for _ in range(100)],
    )
    print("Dataset: \n", dataset)

    # Pytorch manager of data loading, shuffling and batching.
    shuffle = True
    loader = DataLoader(dataset, batch_size=8, shuffle=shuffle)
    print(f"DataLoader: Created with {len(loader)} batches and shuffle enabled? {shuffle}\n", loader)

if __name__ == "__main__":
    main()
