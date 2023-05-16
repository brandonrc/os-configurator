# OS-Configurator

Configurator is a tool for applying configuration layers to a base image.

## User Section

### Prerequisites

- Python 3.7 or higher
- `virt-customize` command-line tool
- `git` (optional, required for importing layers from Git repositories)

### Installation

1. Clone the repository: `git clone https://github.com/brandonrc/configurator.git`
2. Navigate to the project directory: `cd configurator`
3. Install the dependencies: `pip install -r requirements.txt`

### Usage

To apply configuration layers to a base image, use the following command:

```
python configurator.py config <base_image> <os_recipe_toml> <output_image> [--python-version <version>]
```

- `<base_image>`: Path to the base qcow2 image.
- `<os_recipe_toml>`: Path to the OS recipe TOML file.
- `<output_image>`: Path to save the output image.
- `--python-version <version>` (optional): Python version to use for the virtual environment (default is python3).

Ensure that your OS recipe TOML file follows the correct folder structure and naming conventions for the layers to be applied correctly.

Example OS Recipe TOML file:

```toml
[[layers]]
type = "local"
name = "layer1"

[[layers]]
type = "git"
url = "https://github.com/user/repo.git"
branch_or_tag = "main"

[[layers]]
type = "local"
name = "layer2"
```

## Developer Section

### Build and Package

This project uses Poetry as the build and packaging tool. To build and package the project, follow these steps:

1. Install Poetry: `pip install poetry`
2. Build the package: `poetry build`
3. Create a distribution package: `poetry publish`

You can also create RPM and Debian packages using tools like `fpm` or `dpkg`. Please refer to the documentation of those tools for detailed instructions.


