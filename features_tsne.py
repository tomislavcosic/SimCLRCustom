import os

import torch
import torchvision
import argparse

from linear_evaluation import get_features_single_loader
from simclr import SimCLR
from simclr.modules import get_resnet, resnet_v2
from simclr.modules.transformations import TransformsSimCLR
from simclr.modules.transformations.simclr import SimpleTransformsSimCLR
from utils import yaml_config_hook

import numpy as np
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt


def tsne_and_save_as_image(feature_vectors, labels, output_file):
    # Perform t-SNE
    tsne = TSNE(n_components=2, random_state=0)
    tsne_result = tsne.fit_transform(feature_vectors)

    # Plot t-SNE result
    plt.figure(figsize=(8, 6))
    for label in np.unique(labels):
        indices = np.where(labels == label)
        plt.scatter(tsne_result[indices, 0], tsne_result[indices, 1], label=label)
    plt.title('t-SNE Result')
    plt.xlabel('Dimension 1')
    plt.ylabel('Dimension 2')
    plt.legend()

    # Save as image
    plt.savefig(output_file)
    plt.close()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="SimCLR")
    config = yaml_config_hook("./config/config.yaml")
    for k, v in config.items():
        parser.add_argument(f"--{k}", default=v, type=type(v))

    args = parser.parse_args()
    args.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if args.dataset == "STL10":
        train_dataset = torchvision.datasets.STL10(
            args.dataset_dir,
            split="train",
            download=True,
            transform=TransformsSimCLR(size=args.image_size).test_transform,
        )
        test_dataset = torchvision.datasets.STL10(
            args.dataset_dir,
            split="test",
            download=True,
            transform=TransformsSimCLR(size=args.image_size).test_transform,
        )
    elif args.dataset == "CIFAR10":
        train_dataset = torchvision.datasets.CIFAR10(
            args.dataset_dir,
            train=True,
            download=True,
            transform=TransformsSimCLR(size=args.image_size).test_transform,
        )
        test_dataset = torchvision.datasets.CIFAR10(
            args.dataset_dir,
            train=False,
            download=True,
            transform=TransformsSimCLR(size=args.image_size).test_transform,
        )
    else:
        raise NotImplementedError


    test_loader = torch.utils.data.DataLoader(
        test_dataset,
        batch_size=args.logistic_batch_size,
        shuffle=False,
        drop_last=True,
        num_workers=args.workers,
    )

    encoder = resnet_v2.PreActResNet18()
    n_features = encoder.fc.in_features  # get dimensions of fc layer

    # load pre-trained model from checkpoint
    simclr_model = SimCLR(encoder, args.projection_dim, n_features)
    model_fp = os.path.join(args.model_path, "checkpoint_50_no_pretraining.tar".format(args.epoch_num))
    simclr_model.load_state_dict(torch.load(model_fp, map_location=args.device.type))
    simclr_model = simclr_model.to(args.device)
    simclr_model.eval()

    (X, y) = get_features_single_loader(
        simclr_model, test_loader, args.device
    )

    tsne_and_save_as_image(X, y, os.path.join(args.pca_image_output_path, "tsne.png"))
