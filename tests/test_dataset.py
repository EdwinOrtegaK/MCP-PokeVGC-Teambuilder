import pandas as pd

def test_dataset_shape_and_against_keys():
    df = pd.read_csv("data/pokemon.csv")
    assert len(df) >= 700

    against_cols = [c for c in df.columns if c.lower().startswith("against_")]
    if against_cols:
        assert len(against_cols) >= 18
