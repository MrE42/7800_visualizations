import numpy as np
def insert_nan_gaps(x, y, threshold):
    """Insert NaN between time gaps greater than `threshold`."""
    x = np.asarray(x)
    y = np.asarray(y)

    if len(x) < 2:
        return x, y

    dx = np.diff(x)
    gap_indices = np.where(dx > threshold)[0]

    x_new = []
    y_new = []

    for i in range(len(x)):
        x_new.append(x[i])
        y_new.append(y[i])
        if i in gap_indices:
            x_new.append(np.nan)
            y_new.append(np.nan)

    return np.array(x_new), np.array(y_new)
