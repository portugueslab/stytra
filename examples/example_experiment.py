from stytra import Stytra

my_metadata = dict()

if __name__ == "__main__":
    s = Stytra(my_metadata, protocols=[my_protocol])
    s.run()