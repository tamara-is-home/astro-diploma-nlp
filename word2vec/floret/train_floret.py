import typer
from pathlib import Path
import floret

# Run this in CLI as follows: python train_floret.py text.txt vectors
# text.txt is the file with raw text data to train on.
# vectors is the output file name for the word embeddings.
def main(
    input_file: Path,
    output_stem: str,
    mode: str = "floret",
    model: str = "cbow",
    dim: int = 128,
    mincount: int = 1,
    minn: int = 2,
    maxn: int = 5,
    neg: int = 10,
    hashcount: int = 2,
    bucket: int = 2000000,
    thread: int = 8,
    epoch: int = 20,
):
    floret_model = floret.train_unsupervised(
        str(input_file.absolute()),
        model=model,
        mode=mode,
        dim=dim,
        minCount=mincount,
        minn=minn,
        maxn=maxn,
        neg=neg,
        hashCount=hashcount,
        bucket=bucket,
        thread=thread,
        epoch=epoch,
    )
    floret_model.save_model(output_stem + ".bin")
    floret_model.save_vectors(output_stem + ".vec")
    if mode == "floret":
        floret_model.save_floret_vectors(output_stem + ".floret")


if __name__ == "__main__":
    typer.run(main)
