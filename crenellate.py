#%%
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
from dmfwizard.crenellation import crenellate_electrodes
from dmfwizard.types import Electrode

a = Electrode()
b = Electrode()
c = Electrode()
a.points = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
a.origin = (0.0, 0.0)
b.points = [(0.0, -2.0), (2.0, -2.0), (2.0, 4.0), (0.0, 4.0)]
b.origin = (2.0, 0.0)
c.points = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
c.origin = (4.0, 0.0)
NUM_FINGERS = 2
THETA = np.deg2rad(40)

crenellate_electrodes(a, b, NUM_FINGERS, THETA, margin=0.3)
crenellate_electrodes(b, c, 8, THETA, margin=0.3)

print(a.points)
print(b.points)

fig, ax = plt.subplots()
polygons = [Polygon(e.offset_points()) for e in [a, b, c]]
for p in polygons:
    ax.add_patch(p)
ax.set_aspect('equal')
ax.autoscale()



# %%

# %%
