# Vortex FX Generator Add-on

Blender add-on for generating stylized vortex VFX source meshes inspired by dark spiral, abyss rose, nebula, crystal swirl, electric spiral, and petal vortex effects.

## Features

- Generate multiple vortex styles:
  - Abyss Rose
  - Nebula Rift
  - Crystal Swirl
  - Electric Spiral
  - Petal Vortex
  - Random Mix
- Mesh ribbon generation with UVs for game VFX texture workflows
- Electric arc curves
- Core rings
- Spark particles
- Seed-based randomization
- Spin animation keyframes
- Tilt, roll, reverse rotation, alternate direction controls
- Clear generated objects button

## Install

1. Download `addons/vortex_fx_generator_addon.py`.
2. Open Blender.
3. Go to `Edit > Preferences > Add-ons > Install...`.
4. Select the Python file.
5. Enable `Vortex FX Generator`.
6. Open the 3D Viewport sidebar with `N`.
7. Go to `VFX > Vortex FX Generator`.

## Basic Usage

1. Click `Preset: Dark Spiral Like Reference` for a dark purple spiral similar to the reference.
2. Click `Generate Vortex FX`.
3. Adjust arms, layers, radius, ribbon width, swirl, noise, jaggedness, color, glow, and animation settings.
4. Use `Random` to explore variations.
5. Export generated mesh/curve objects as FBX if needed for game VFX workflows.

## Notes

The generated ribbons include UVs with U along the spiral and V across the ribbon width. This is useful for scrolling or masking textures in a game engine.
