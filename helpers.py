import numpy as np
from functools import lru_cache

def setseed(seed):
    """
    Sets the seed for reproducibility.
    """
    np.random.seed(seed)
    # Cache invalidation (it wrong)
    get_gradients.cache_clear()
    fade_cached.cache_clear()

@lru_cache(maxsize=16)
def get_gradients(scale):
    # Gradients only depend on scale
    return np.random.uniform(-1, 1, scale + 1)

@lru_cache(maxsize=128)
def fade_cached(t):
    # t is a float, so round to avoid cache misses due to float precision
    t = round(t, 6)
    return 6*t**5 - 15*t**4 + 10*t**3

def perlin(x, scale=1):
    """
    Returns 1D Perlin-like noise value at position x.
    Args:
        x (float): Position on the noise line.
        scale (int): Scale of the noise.
    Returns:
        float: Noise value in range [0, scale].
    """
    gradients = get_gradients(5)
    x0 = int(np.floor(x)) % 5
    x1 = (x0 + 1) % 5
    t = x - np.floor(x)

    fade_t = fade_cached(t)

    def lerp(a, b, t):
        return a + t * (b - a)

    g0 = gradients[x0]
    g1 = gradients[x1]
    d0 = t
    d1 = t - 1
    n0 = g0 * d0
    n1 = g1 * d1
    noise = lerp(n0, n1, fade_t)
    # Normalize from [-1,1] to [0,1]
    noise = (noise + 1) / 2
    return noise * scale