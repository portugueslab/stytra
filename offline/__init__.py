import numpy as np
import json
from pathlib import Path
import pandas as pd


class Metadata(dict):
    """

    Parameters
    ----------
    path :


    Returns
    -------

    """

    def __init__(self, path):
        # Prepare path:
        if not isinstance(path, Path):
            self.path = Path(path)
        else:
            self.path = path
        meta_files = list(self.path.glob("*metadata.json"))

        # Load metadata:
        if len(meta_files) == 0:
            raise FileNotFoundError("No metadata file in specified path!")
        elif len(meta_files) > 1:
            raise FileNotFoundError("Multiple metadata files in specified path!")
        else:
            with open(str(meta_files[0]), "r") as f:
                self.source_metadata = json.load(f)

        metadata = self.source_metadata.copy()

        # Temporary workaround:
        metadata["behavior"] = metadata.pop("tracking")

        super().__init__(**metadata)

        # Look for additional files with experiment info such as tracking
        #  or dynamic log:
        exp_tag = meta_files[0].parts[-1].split("_")[0]
        all_files = list(self.path.glob("{}*".format(exp_tag)))
        self.log_ids = [
            "_".join(f.parts[-1].split("_")[1:]).split(".")[0] for f in all_files
        ]
        self.log_ids.pop(self.log_ids.index("metadata"))

        for l_id in self.log_ids:
            self.__setitem__(l_id, None)

    def __getitem__(self, key):
        """

        Parameters
        ----------
        key :


        Returns
        -------

        """
        # if we ask for data in the files, here they are loaded and set:
        if key in self.log_ids:
            if super().__getitem__(key) is None:
                super().__setitem__(key, self._load_data(key))

        return super().__getitem__(key)

    @staticmethod
    def resample(df_in, resample_sec=0.005):
        """

        Parameters
        ----------
        df_in :
        resample_sec :


        Returns
        -------

        """
        df = df_in.copy()
        t_index = pd.to_timedelta(
            (df["t"].as_matrix() * 10e5).astype(np.uint64), unit="us"
        )
        df.set_index(t_index - t_index[0], inplace=True)
        df = df.resample("{}ms".format(int(resample_sec * 1000))).mean()
        df.index = df.index.total_seconds()
        return df.interpolate().drop("t", axis=1)

    def _load_data(self, data_name):
        """

        Parameters
        ----------
        data_name :


        Returns
        -------

        """

        file = next(self.path.glob("*{}*".format(data_name)))
        if file.parts[-1].split(".")[-1] == "csv":
            return pd.read_csv(str(file), delimiter=";").drop("Unnamed: 0", axis=1)
        elif file.parts[-1].split(".")[-1] == "h5":
            pass  # implement
