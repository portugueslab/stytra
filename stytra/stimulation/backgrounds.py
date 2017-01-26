import numpy as np


def noise_background(size, kernel_std_x=1, kernel_std_y=None):
    if kernel_std_y is None:
        kernel_std_y = kernel_std_x
    width_kernel_x = size[0]
    width_kernel_y = size[1]
    kernel_gaussian_x = np.exp(
        - (np.arange(
            width_kernel_x) - width_kernel_x / 2) ** 2 / kernel_std_x ** 2)
    kernel_gaussian_y = np.exp(
        - (np.arange(
            width_kernel_y) - width_kernel_y / 2) ** 2 / kernel_std_y ** 2)

    kernel_2D = kernel_gaussian_x[None, :] * kernel_gaussian_y[:, None]

    img = np.random.randn(*size)
    img = np.real(np.fft.ifft2(np.fft.fft2(img) * np.fft.fft2(kernel_2D)))

    min_im = np.min(img)
    max_im = np.max(img)
    return (((img - min_im) / (max_im - min_im)) * 255).astype(np.uint8)