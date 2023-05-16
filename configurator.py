import argparse
import os
import subprocess
import tarfile
import tempfile
import urllib.parse
import toml
import os
from pathlib import Path
import shutil


import shutil

def check_dependencies():
    dependencies = ['virt-customize', 'git']
    missing_dependencies = []

    for dependency in dependencies:
        if shutil.which(dependency) is None:
            missing_dependencies.append(dependency)

    if missing_dependencies:
        print("Warning: The following dependencies are missing:")
        for dependency in missing_dependencies:
            print(f"- {dependency}")
        print("Please install the missing dependencies before running this application.")
        
def check_qcow2_file(file):
    if not os.path.isfile(file):
        raise argparse.ArgumentTypeError(f"{file} does not exist")
    if not file.endswith('.qcow2'):
        raise argparse.ArgumentTypeError(f"{file} is not a .qcow2 file")
    return file

def create_arg_parser():
    parser = argparse.ArgumentParser(prog="configurator")

    subparsers = parser.add_subparsers(dest='command')

    # Existing 'config' command
    config_parser = subparsers.add_parser('config')
    config_parser.add_argument("base_image", type=str, help="Path to the base qcow2 image.")
    config_parser.add_argument("os_recipe_toml", type=str, help="Path to the OS recipe TOML file.")
    config_parser.add_argument("output_image", type=str, help="Path to save the output image.")
    config_parser.add_argument("--python-version", type=str, default='python3', help="Python version to use for the virtual environment.")

    # New 'layers' command
    layers_parser = subparsers.add_parser('layers')
    layers_subparsers = layers_parser.add_subparsers(dest='layers_command')

    # 'layers list' command
    layers_list_parser = layers_subparsers.add_parser('list')

    # 'layers import' command
    layers_import_parser = layers_subparsers.add_parser('import')
    layers_import_parser.add_argument("git_url", type=str, help="Git URL to import.")

    return parser

def get_requirements_files(layer, file_name):
    file_path = os.path.join(layer, 'package-lists', file_name)
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return [line.strip() for line in file if line.strip() and not line.startswith('#')]
    return []

def list_layers():
    # Get the current user's home directory
    home_dir = Path.home()

    # Define the cache directory path
    cache_dir = home_dir / ".cache" / "myapp"

    print(f"{'Layer Name':<20} {'Source':<20}")

    # List layers in the 'layers' directory
    layers_dir = Path('layers')
    if layers_dir.exists():
        for item in layers_dir.iterdir():
            if item.is_dir():
                print(f'{item.name:<20} {"Configurator":<20}')

    # List layers in the cache directory
    if cache_dir.exists():
        for item in cache_dir.iterdir():
            if item.is_dir():
                # Get the origin URL of the git repository
                git_url = subprocess.getoutput(f'git -C {item} config --get remote.origin.url')
                print(f'{item.name:<20} {git_url:<20}')

def import_layer(git_url):
    # Parse the name of the repository from the URL
    layer_name = urllib.parse.urlparse(git_url).path.strip('/').split('/')[-1]

    # Get the current user's home directory
    home_dir = Path.home()

    # Define the cache directory path
    cache_dir = home_dir / ".cache" / "myapp"

    # Create the cache directory if it doesn't exist
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Define the local path where the repository should be cloned
    local_layer_path = cache_dir / layer_name

    if not local_layer_path.exists():
        # If the repository isn't already cloned, clone it
        subprocess.run(['git', 'clone', git_url, local_layer_path])
    else:
        # If the repository is already cloned, pull the latest changes
        subprocess.run(['git', '-C', local_layer_path, 'pull'])

def apply_layers(base_image, os_recipe_toml, output_image, python_version):
    with open(os_recipe_toml, 'r') as file:
        recipe = toml.load(file)
        
    rpm_requirements = []
    deb_requirements = []
    pip_requirements = []

    config_layers = recipe['layers']

    # Get the current user's home directory
    home_dir = Path.home()

    # Define the cache directory path
    cache_dir = home_dir / ".cache" / "myapp"

    # Create the cache directory if it doesn't exist
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Extract the layers from the recipe
    config_layers = recipe['layers']

    with tempfile.NamedTemporaryFile(suffix=".tar.gz") as temp_file:
        with tarfile.open(temp_file.name, "w:gz") as tar:
            for layer in config_layers:
                if layer['type'] == 'git':
                    layer_name = urllib.parse.urlparse(layer['url']).path.strip('/').split('/')[-1]
                    local_layer_path = os.path.join(cache_dir, layer_name)
                    if not os.path.exists(local_layer_path):
                        subprocess.run(['git', 'clone', '-b', layer['branch_or_tag'], layer['url'], local_layer_path])
                    else:
                        subprocess.run(['git', '-C', local_layer_path, 'pull'])
                    layer_path = local_layer_path
                else:
                    layer_path = os.path.join('layers', layer['name'])

                rpm_requirements += get_requirements_files(layer_path, 'rpm-requirements.txt')
                deb_requirements += get_requirements_files(layer_path, 'dpm-requirements.txt')
                pip_requirements += get_requirements_files(layer_path, 'pip-requirements.txt')

                config_dir = os.path.join(layer_path, 'configs')
                if not os.path.exists(config_dir):
                    print(f"Config directory not found in layer: {layer['name']}")
                    continue

                tar.add(config_dir, arcname=f'{layer["name"]}')

        subprocess.run(['virt-customize', '-a', base_image, '--upload', f'{temp_file.name}:/'])
        subprocess.run(['virt-customize', '-a', base_image, '--run-command', f'tar xzf /{os.path.basename(temp_file.name)} -C /'])


    if rpm_requirements:
        subprocess.run(['virt-customize', '-a', base_image, '--run-command', f'dnf install -y {" ".join(rpm_requirements)}'])

    if deb_requirements:
        subprocess.run(['virt-customize', '-a', base_image, '--run-command', f'apt-get install -y {" ".join(deb_requirements)}'])

    if pip_requirements:
        subprocess.run(['virt-customize', '-a', base_image, '--run-command', f'{python_version} -m venv /opt/os-python-venv'])
        subprocess.run(['virt-customize', '-a', base_image, '--run-command', f'source /opt/os-python-venv/bin/activate && pip install {" ".join(pip_requirements)}'])
        subprocess.run(['virt-customize', '-a', base_image, '--run-command', 'chmod -R 777 /opt/os-python-venv'])

    subprocess.run(['cp', base_image, output_image])

def main():
    check_dependencies()
    parser = create_arg_parser()
    args = parser.parse_args()

    if args.command == 'config':
        apply_layers(args.base_image, args.os_recipe_toml, args.output_image, args.python_version)
    elif args.command == 'layers':
        if args.layers_command == 'list':
            list_layers()
        elif args.layers_command == 'import':
            import_layer(args.git_url)

if __name__ == '__main__':
    main()
