import numpy as np
import random
from math import sqrt, pi, sin, cos
from itertools import product
from PIL import Image, ImageDraw
import deepdish.io as dio
import cv2
import logging


def noise_background(size, kernel_std_x=1, kernel_std_y=None):
    """

    Parameters
    ----------
    size :
        
    kernel_std_x :
         (Default value = 1)
    kernel_std_y :
         (Default value = None)

    Returns
    -------

    """
    if kernel_std_y is None:
        kernel_std_y = kernel_std_x
    width_kernel_x = size[0]
    width_kernel_y = size[1]
    kernel_gaussian_x = np.exp(
        -(np.arange(width_kernel_x) - width_kernel_x / 2) ** 2 / kernel_std_x ** 2
    )
    kernel_gaussian_y = np.exp(
        -(np.arange(width_kernel_y) - width_kernel_y / 2) ** 2 / kernel_std_y ** 2
    )

    kernel_2D = kernel_gaussian_x[None, :] * kernel_gaussian_y[:, None]

    img = np.random.randn(*size)
    img = np.real(np.fft.ifft2(np.fft.fft2(img) * np.fft.fft2(kernel_2D)))

    min_im = np.min(img)
    max_im = np.max(img)
    return (((img - min_im) / (max_im - min_im)) * 255).astype(np.uint8)


def existing_file_background(filepath):
    """ Returns a numpy array from an image stored at filepath
    """
    if filepath.endswith(".h5"):
        return dio.load(filepath)
    else:
        # If using OpenCV, we have to get RGB, not BGR
        try:
            return cv2.imread(filepath)[:, :, [2, 1, 0]]
        except TypeError:
            log = logging.getLogger()
            log.info("Could nor load " + filepath)
            return np.zeros((10, 10), dtype=np.uint8)


def poisson_disk_background(size, distance, radius):
    """A background with randomly spaced dots using the poisson disk
     algorithm

    Parameters
    ----------
    size :
        image size
    distance :
        approximate distance between the dots
    radius :
        radius of the dots

    Returns
    -------
    type
        the generated background

    """

    imh = size[0]
    imw = size[1]

    # first make the points
    g = Grid(distance, *size)
    rand = (random.uniform(0, imh), random.uniform(0, imw))
    data = g.poisson(rand)

    # then put them on a 2x size image, so that a seamless background can
    # be created:

    im = Image.new("L", (imh * 2, imw * 2))

    dr = ImageDraw.Draw(im)

    points0 = np.array(data)
    points = np.array([])
    for i in range(2):
        for j in range(2):
            if len(points) == 0:
                points = points0 + np.array([imh * i, imw * j])
            else:
                points = np.concatenate(
                    [points, points0 + np.array([imh * i, imw * j])]
                )
    for point in points:
        dr.ellipse([tuple(point - radius), tuple(point + radius)], fill=255)

    return np.array(im)[imh // 2 : 3 * imh // 2, imw // 2 : 3 * imw // 2]


def gratings(
    mm_px=1, spatial_period=10, orientation="horizontal", shape="square", ratio=0.5
):
    """Function for generating grids (assume usage of cv2.BORDER_WRAP for display)

    Parameters
    ----------
    mm_px :
        millimiters per pixel (Default value = 1)
    spatial_period :
        spatial period (cycles/mm) (Default value = 10)
    orientation :
        horizontal' or 'vertical' (Default value = 'horizontal')
    shape :
        square', 'sinusoidal' (Default value = 'square')
    ratio :
        ratio of white over dark (Default value = 0.5)

    Returns
    -------

    """

    grating_dim = round(spatial_period / (mm_px))  # calculate dimensions

    # With cv2.BORDER_WRAP 1 line will be enough:
    template_array = np.zeros((grating_dim, 1), dtype=np.uint8)

    # Set pixels values according to the selected shape:
    if shape == "square":  # square wave
        template_array[: round(ratio * grating_dim), :] = 255

    elif shape == "sinusoidal":  # sinusoidal wave
        v = (np.sin(np.linspace(0, 2 * np.pi, grating_dim)) + 1) * 255 / 2
        template_array[:, 0] = v.astype("uint8")

    # Transpose for having vertical gratings:
    if orientation == "vertical":
        template_array = template_array.T

    return template_array


class Grid:
    """class for filling a rectangular prism of dimension >= 2
    with poisson disc samples spaced at least r apart
    and k attempts per active sample
    override Grid.distance to change
    distance metric used and get different forms
    of 'discs'
    
    Adapted from code by Herman Tulleken (herman@luma.co.za)

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self, r, *size):
        self.r = r

        self.size = size
        self.dim = len(size)

        self.cell_size = r / (sqrt(self.dim))

        self.widths = [int(size[k] / self.cell_size) + 1 for k in range(self.dim)]

        nums = product(*(range(self.widths[k]) for k in range(self.dim)))

        self.cells = {num: -1 for num in nums}
        self.samples = []
        self.active = []

    def clear(self):
        """resets the grid
        active points and
        sample points

        Parameters
        ----------

        Returns
        -------

        """
        self.samples = []
        self.active = []

        for item in self.cells:
            self.cells[item] = -1

    def generate(self, point):
        """generates new points
        in an annulus between
        self.r, 2*self.r

        Parameters
        ----------
        point :
            

        Returns
        -------

        """

        rad = random.triangular(self.r, 2 * self.r, .3 * (2 * self.r - self.r))
        # was random.uniform(self.r, 2*self.r) but I think
        # this may be closer to the correct distribution
        # but easier to build

        angs = [random.uniform(0, 2 * pi)]

        if self.dim > 2:
            angs.extend(random.uniform(-pi / 2, pi / 2) for _ in range(self.dim - 2))

        angs[0] = 2 * angs[0]

        return self.convert(point, rad, angs)

    def poisson(self, seed, k=30):
        """generates a set of poisson disc samples

        Parameters
        ----------
        seed :
            
        k :
             (Default value = 30)

        Returns
        -------

        """
        self.clear()

        self.samples.append(seed)
        self.active.append(0)
        self.update(seed, 0)

        while self.active:

            idx = random.choice(self.active)
            point = self.samples[idx]
            new_point = self.make_points(k, point)

            if new_point:
                self.samples.append(tuple(new_point))
                self.active.append(len(self.samples) - 1)
                self.update(new_point, len(self.samples) - 1)
            else:
                self.active.remove(idx)

        return self.samples

    def make_points(self, k, point):
        """uses generate to make up to
        k new points, stopping
        when it finds a good sample
        using self.check

        Parameters
        ----------
        k :
            
        point :
            

        Returns
        -------

        """
        n = k

        while n:
            new_point = self.generate(point)
            if self.check(point, new_point):
                return new_point

            n -= 1

        return False

    def check(self, point, new_point):
        """checks the neighbors of the point
        and the new_point
        against the new_point
        returns True if none are closer than r

        Parameters
        ----------
        point :
            
        new_point :
            

        Returns
        -------

        """
        for i in range(self.dim):
            if not (0 < new_point[i] < self.size[i] or self.cellify(new_point) == -1):
                return False

        for item in self.neighbors(self.cellify(point)):
            if self.distance(self.samples[item], new_point) < self.r ** 2:
                return False

        for item in self.neighbors(self.cellify(new_point)):
            if self.distance(self.samples[item], new_point) < self.r ** 2:
                return False

        return True

    def convert(self, point, rad, angs):
        """converts the random point
        to rectangular coordinates
        from radial coordinates centered
        on the active point

        Parameters
        ----------
        point :
            
        rad :
            
        angs :
            

        Returns
        -------

        """
        new_point = [point[0] + rad * cos(angs[0]), point[1] + rad * sin(angs[0])]
        if len(angs) > 1:
            new_point.extend(
                point[i + 1] + rad * sin(angs[i]) for i in range(1, len(angs))
            )
        return new_point

    def cellify(self, point):
        """returns the cell in which the point falls

        Parameters
        ----------
        point :
            

        Returns
        -------

        """
        return tuple(point[i] // self.cell_size for i in range(self.dim))

    def distance(self, tup1, tup2):
        """returns squared distance between two points

        Parameters
        ----------
        tup1 :
            
        tup2 :
            

        Returns
        -------

        """
        return sum(
            min(abs(tup1[k] - tup2[k]), self.size[k] - abs(tup1[k] - tup2[k])) ** 2
            for k in range(self.dim)
        )

    def cell_distance(self, tup1, tup2):
        """returns true if the L1 distance is less than 2
        for the two tuples

        Parameters
        ----------
        tup1 :
            
        tup2 :
            

        Returns
        -------

        """
        return (
            sum(
                min(abs(tup1[k] - tup2[k]), self.widths[k] - abs(tup1[k] - tup2[k]) - 1)
                for k in range(self.dim)
            )
            <= 2
        )

    def neighbors(self, cell):
        """finds all occupied cells within
        a distance of the given point

        Parameters
        ----------
        cell :
            

        Returns
        -------

        """
        return (
            self.cells[tup]
            for tup in self.cells
            if self.cells[tup] != -1 and self.cell_distance(cell, tup)
        )

    def update(self, point, index):
        """updates the grid with the new point

        Parameters
        ----------
        point :
            
        index :
            

        Returns
        -------

        """
        self.cells[self.cellify(point)] = index

    def __str__(self):
        return self.cells.__str__()


if __name__ == "__main__":
    bg = 255 - poisson_disk_background((640, 640), 12, 2)
    dio.save("poisson_dense.h5", bg)
