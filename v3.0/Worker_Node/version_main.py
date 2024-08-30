from flask import Flask, jsonify,request,session
import subprocess
import jwt
from functools import wraps
from flask_cors import CORS
import socket
import docker
import os
import  random
#############################Function Start #####################################
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token,"QubridLLC", algorithms=['HS256'])
            print(data)
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(*args, **kwargs)
    return decorated

# Function to execute shell commands and return output
def run_command(command):
    try:
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return result.stderr.strip()
    except Exception as e:
        return str(e)

#return jsonify(nvidia-smi -q -d compute| grep "^CUDA Version")
##################################################Get System details ###################################################
########################@app.route('/cpu_info')
@app.route('/cpu_info')
def get_cpu_info():
    command = "lscpu |grep Core |awk '{print $4}'"
    return jsonify({'cpu_info': run_command(command)})

@app.route('/ram_info')
def get_ram_size():
    command = "free -h |grep 'Mem' | awk '{print $2}'"
    return jsonify({'ram_info': run_command(command)})
#################

@app.route('/hostname')
@token_required
def get_hostname():
    return jsonify({'hostname': subprocess.getoutput("hostname")})

@app.route('/kernel_version')
@token_required
def get_kernel_version():
    return jsonify({'kernel_version': subprocess.getoutput("uname -r")})
#################################################################################
@app.route('/system_info')
@token_required
def get_system_info():
    commands = {
        "cpu_name": "lscpu |grep Model |awk '{print $3 $4}'",
        "cpu_info": "lscpu |grep Core |awk '{print $4}'",
        "python_version": "python3 --version",
        "os_version": "cat /etc/os-release | grep PRETTY_NAME=",
        "root_size": "df -h / | awk '{ print $2 }' | tail -n 1",
        "ram_size": "free -h | grep 'Mem' | awk '{print $2}'",
        "uptime": "uptime -p | awk '{print $2 $3 $4 $5}'"
    }

    results = {}
    for key, command in commands.items():
        results[key] = run_command(command)

    return jsonify(results)

################################################################################
@app.route('/gpu_info')
#@token_required
def get_gpu_info():
    try:
        # Check if any NVIDIA GPU is detected
        lspci_command = "lspci | grep NVIDIA"
        gpu_detected = run_command(lspci_command)

        if not gpu_detected:
            return jsonify({'gpu_info': 'No NVIDIA GPU detected'}), 200

        # Check if NVIDIA driver is installed
        nvidia_smi_command = "nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1"
        gpu_info = run_command(nvidia_smi_command)

        if not gpu_info:
            return jsonify({'gpu_info': 'GPU detected but driver not installed'}), 200

        return jsonify({'gpu_info': gpu_info}), 200

    except Exception as e:
        return jsonify({"gpu_info": str(e)}), 500

#######################################################################################
@app.route('/gpu_count')
@token_required
def get_gpu_count():
    try:
        # Check if any NVIDIA GPU is detected
        lspci_command = "lspci | grep NVIDIA"
        gpu_detected = run_command(lspci_command)

        if not gpu_detected:
            return jsonify({'gpu_count': 'No NVIDIA GPU detected'}), 200

        # Check if NVIDIA driver is installed
        nvidia_smi_command = "nvidia-smi --query-gpu=count --format=csv,noheader | head -n 1"
        gpu_count = run_command(nvidia_smi_command)

        if not gpu_count:
            return jsonify({'gpu_count': 'GPU detected but driver not installed'}), 200

        return jsonify({'gpu_count': gpu_count}), 200

    except Exception as e:
        return jsonify({"gpu_count": str(e)}), 500


###################################################################################################


@app.route('/nvidia_driver_version')
@token_required
def get_nvidia_driver_version():
    command = "nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -n 1"
    driver_version = run_command(command)
    if not driver_version:
        return jsonify({'nvidia_driver': 'Nvidia-driver not found'})
    return jsonify({'nvidia_driver': driver_version})


##cuda function return jsonify(nvidia-smi -q -d compute| grep "^CUDA Version") 
@app.route('/nvidia_cuda_version')
@token_required
def get_nvidia_cuda_version():
    command = "nvidia-smi -q -d compute| grep CUDA |awk '{print $4}'"
    cuda_version = run_command(command)
    if not cuda_version:
        return jsonify({'cuda_driver': 'cuda not installed'})
    return jsonify({'cuda_driver': cuda_version})



@app.route('/cuda_version')
@token_required
def get_cuda_version():
    command = "nvcc --version | grep 'release'"
    cuda_output = run_command(command)
    return jsonify({'cuda_version': cuda_output.split()[5] if cuda_output else "CUDA version not found"})

@app.route('/docker_version')
@token_required
def get_docker_version():
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return jsonify({'docker_version': result.stdout.strip()})
        else:
            return jsonify({'docker_version': result.stderr.strip()})
    except FileNotFoundError:
        return jsonify({'docker_version': "Docker not found"})

########################################## FUNCTION FOR INSTALL NVIDIA-DRIVER ########################################
@app.route('/install-nvidia-driver-545', methods=['POST'])
@token_required
def nvidia_install():
    try:
        # Function to run shell commands
        def run_command(command):
            import subprocess
            print(f"Running command: {command}")
            result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode('utf-8')
            print(f"Command output: {output}")
            return output

        # Check if NVIDIA GPU is present
        lspci_command = "lspci | grep -i nvidia"
        gpu_present = run_command(lspci_command)

        if not gpu_present:
            return jsonify({'message': 'GPU is not found'}), 404

        # Check if NVIDIA driver is installed
        nvidia_smi_command = "nvidia-smi |grep 12.3"
        driver_installed = run_command(nvidia_smi_command)

        if driver_installed:
            return jsonify({'message': 'NVIDIA driver is already installed'}), 200

        # Commands to remove CUDA and NVIDIA packages and install new drivers
        commands = [
            'sudo apt-get --purge remove "*cuda*" "*cublas*" "*cufft*" "*cufile*" "*curand*" "*cusolver*" "*cusparse*" "*gds-tools*" "*npp*" "*nvjpeg*" "nsight*" "*nvvm*" -y',
            'sleep 5',
            'sudo apt-get --purge remove "*nvidia-smi*" "libxnvctrl*" -y',
            'sleep 5',
            'sudo apt-get autoremove -y',
            'sleep 10',
            'sudo apt-get --purge remove cuda-* nvidia-smi* gds-tools-* libcublas-* libcufft-* libcufile-* libcurand-* libcusolver-* libcusparse-* libnpp-* libnvidia-* libnvjitlink-* libnvjpeg-* nsight* nvidia-smi* libnvidia-* libcudnn8* -y',
            'sleep 5',
            'sudo apt-get --purge remove "*cublas*" "*cufft*" "*curand*" "*cusolver*" "*cusparse*" "*npp*" "*nvjpeg*" "cuda*" "nsight*" -y',
            'sudo apt-get autoremove -y',
            'sudo apt-get autoclean -y',
            'sudo rm -rf /usr/local/cuda*',
            'sudo dpkg -r cuda',
            'sudo dpkg -r $(dpkg -l | grep \'^ii  cudnn\' | awk \'{print $2}\')',
            'wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin',
            'sleep 5',
            'sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600',
            'wget https://developer.download.nvidia.com/compute/cuda/12.3.0/local_installers/cuda-repo-ubuntu2204-12-3-local_12.3.0-545.23.06-1_amd64.deb',
            'sleep 5',
            'sudo dpkg -i cuda-repo-ubuntu2204-12-3-local_12.3.0-545.23.06-1_amd64.deb',
            'sudo cp /var/cuda-repo-ubuntu2204-12-3-local/cuda-*-keyring.gpg /usr/share/keyrings/',
            'sleep 5',
            'sudo apt-get update',
            'sudo rm -rf cuda-repo-ubuntu2204-12-3-local_12.3.0-545.23.06-1_amd64.deb',
            'sleep 5',
            'sudo apt-get -y install cuda-toolkit-12-3',
            'sleep 5',
            'sudo apt-get install -y nvidia-kernel-open-545',
            'sleep 5',
            'sudo apt-get install -y cuda-drivers-545',
            'sleep 5',
            'sudo apt-get install -y nvidia-container-toolkit',
            'sleep 5',
            'sudo systemctl restart docker',
            'sleep 5',
            'sudo reboot'
        ]
        #command_outputs = []

        for command in commands:
            run_command(command)
            #output = run_command(command)
            #command_outputs.append(output)


        return jsonify({"message": "Successfully installed CUDA and NVIDIA drivers"}), 200

    except Exception as e:
       # logger.exception("Exception occurred during installation")
        return jsonify({"message": str(e)}), 500

######################################################
@app.route('/install-nvidia-driver-550', methods=['POST'])
@token_required
def driver_install():
    try:
        # Check if NVIDIA GPU is present
        lspci_command = "lspci | grep -i nvidia"
        gpu_present = run_command(lspci_command)

        if not gpu_present:
            return jsonify({'message': 'GPU is not found'}), 404

        # Check if NVIDIA driver is installed
        nvidia_smi_command = "nvidia-smi |grep 12.4"
        driver_installed = run_command(nvidia_smi_command)

        if driver_installed:
            return jsonify({'message': 'NVIDIA driver is already installed'}), 200

        # Commands to remove CUDA and NVIDIA packages and install new drivers
        commands = [
            'sudo apt-get --purge remove "*cuda*" "*cublas*" "*cufft*" "*cufile*" "*curand*" "*cusolver*" "*cusparse*" "*gds-tools*" "*npp*" "*nvjpeg*" "nsight*" "*nvvm*" -y',
            'sleep 5',
            'sudo apt-get --purge remove "*nvidia-smi*" "libxnvctrl*" -y',
            'sleep 5',
            'sudo apt-get autoremove -y',
            'sleep 10',
            'sudo apt-get --purge remove cuda-* nvidia-smi* gds-tools-* libcublas-* libcufft-* libcufile-* libcurand-* libcusolver-* libcusparse-* libnpp-* libnvidia-* libnvjitlink-* libnvjpeg-* nsight* nvidia-smi* libnvidia-* libcudnn8* -y',
            'sleep 5',
            'sudo apt-get --purge remove "*cublas*" "*cufft*" "*curand*" "*cusolver*" "*cusparse*" "*npp*" "*nvjpeg*" "cuda*" "nsight*" -y',
            'sudo apt-get autoremove -y',
            'sudo apt-get autoclean -y',
            'sudo rm -rf /usr/local/cuda*',
            'sudo dpkg -r cuda',
            'sudo dpkg -r $(dpkg -l | grep \'^ii  cudnn\' | awk \'{print $2}\')',
            # Download and install new CUDA and NVIDIA drivers

            'wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin',
            'sleep 5',
            'sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600',
            'sleep 5',
            'wget https://developer.download.nvidia.com/compute/cuda/12.4.1/local_installers/cuda-repo-ubuntu2204-12-4-local_12.4.1-550.54.15-1_amd64.deb',
            'sudo dpkg -i cuda-repo-ubuntu2204-12-4-local_12.4.1-550.54.15-1_amd64.deb',
            'sudo cp /var/cuda-repo-ubuntu2204-12-4-local/cuda-*-keyring.gpg /usr/share/keyrings/',
            'sleep5',
            'sudo apt-get update',
            'sudo rm -rf cuda-repo-ubuntu2204-12-4-local_12.4.1-550.54.15-1_amd64.deb',
            'sleep 5',
            'sudo apt-get -y install cuda-toolkit-12-4',
            'sleep 5',
            'sudo apt-get install -y nvidia-driver-550-open',
            'sleep 5',
            'sudo apt-get install -y cuda-drivers-550',
            'sleep 5',
            'sudo apt-get install -y nvidia-container-toolkit',
            'sleep 5',
            'sudo systemctl restart docker',
            'sleep 5',
            'sudo reboot'
        ]
        #command_outputs = []

        for command in commands:
            run_command(command)
            #output = run_command(command)
            #command_outputs.append(output)
        return jsonify({"message": "Successfully installed CUDA and NVIDIA drivers"}), 200

    except Exception as e:
       # logger.exception("Exception occurred during installation")
        return jsonify({"message": str(e)}), 500

##################################

@app.route('/install-nvidia-driver-555', methods=['POST'])
@token_required
def nvidia_cuda_install():
    try:
        # Check if NVIDIA GPU is present
        lspci_command = "lspci | grep -i nvidia"
        gpu_present = run_command(lspci_command)

        if not gpu_present:
            return jsonify({'message': 'GPU is not found'}), 404

        # Check if NVIDIA driver is installed
        nvidia_smi_command = "nvidia-smi | grep 12.5"
        driver_installed = run_command(nvidia_smi_command)

        if driver_installed:
            return jsonify({'message': 'NVIDIA driver is already installed'}), 200

        # Commands to remove CUDA and NVIDIA packages and install new drivers
        commands = [
            'sudo apt-get --purge remove "*cuda*" "*cublas*" "*cufft*" "*cufile*" "*curand*" "*cusolver*" "*cusparse*" "*gds-tools*" "*npp*" "*nvjpeg*" "nsight*" "*nvvm*" -y',
            'sleep 5',
            'sudo apt-get --purge remove "*nvidia-smi*" "libxnvctrl*" -y',
            'sleep 5',
            'sudo apt-get autoremove -y',
            'sleep 10',
            'sudo apt-get --purge remove cuda-* nvidia-smi* gds-tools-* libcublas-* libcufft-* libcufile-* libcurand-* libcusolver-* libcusparse-* libnpp-* libnvidia-* libnvjitlink-* libnvjpeg-* nsight* nvidia-smi* libnvidia-* libcudnn8* -y',
            'sleep 5',
            'sudo apt-get --purge remove "*cublas*" "*cufft*" "*curand*" "*cusolver*" "*cusparse*" "*npp*" "*nvjpeg*" "cuda*" "nsight*" -y',
            'sleep 5',
            'sudo apt-get autoremove -y',
            'sleep 5',
            'sudo apt-get autoclean -y',
            'sudo rm -rf /usr/local/cuda*',
            'sudo dpkg -r cuda',
            'sudo dpkg -r $(dpkg -l | grep \'^ii  cudnn\' | awk \'{print $2}\')',
            # Download and install new CUDA and NVIDIA drivers
            'sudo wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin',
            'sleep 5',
            'sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600',
            'sleep 5',
            'wget https://developer.download.nvidia.com/compute/cuda/12.5.0/local_installers/cuda-repo-ubuntu2204-12-5-local_12.5.0-555.42.02-1_amd64.deb',
            'sleep 5',
            'sudo dpkg -i cuda-repo-ubuntu2204-12-5-local_12.5.0-555.42.02-1_amd64.deb',
            'sleep 5',
            'sudo cp /var/cuda-repo-ubuntu2204-12-5-local/cuda-*-keyring.gpg /usr/share/keyrings/',
            'sleep 5',
            'sudo apt-get update',
            'sudo rm -rf cuda-repo-ubuntu2204-12-5-local_12.5.0-555.42.02-1_amd64.deb',
            'sleep 5',
            'sudo apt-get -y install cuda-toolkit-12-5',
            'sleep 5',
            'sudo apt-get install -y nvidia-driver-555-open',
            'sleep 5',
            'sudo apt-get install -y cuda-drivers-555',
            'sleep 5',
            'sudo apt-get install -y nvidia-container-toolkit',
            'sleep 5',
            'sudo systemctl restart docker',
            'sleep 5',
            'sudo reboot'
        ]
   #     command_outputs = []
        for command in commands:
            run_command(command)
    #        output = run_command(command)
     #       logger.info(f"Command output: {output}")

        return jsonify({"message": "Successfully installed CUDA and NVIDIA drivers"}), 200

    except Exception as e:
      #  logger.exception("Exception occurred during installation")
        return jsonify({"message": str(e)}), 500

#########################################UNINSTALLED NVIDIA-DRIVER ####################################################


######################################## Package Updates #####################################################

@app.route('/nvidia_update_driver')
@token_required
def get_nvidia_update_version():
    try:
        # Check if any NVIDIA GPU is detected
        lspci_command = "nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -n 1"
        gpu_detected = run_command(lspci_command)

        if not gpu_detected:
            return jsonify({'nvidia_update_driver': 'NVIDIA Driver not install on the host machine'}), 200

        # Check if NVIDIA driver is installed
        nvidia_smi_command = "apt list --upgradable |grep nvidia-driver | awk '{print $1, $2}' |tail -n 1"
        nvidia_update_driver = run_command(nvidia_smi_command)

        if not nvidia_update_driver:
            return jsonify({'nvidia_update_driver': 'NVIDIA Driver up to date'}), 200

        return jsonify({'nvidia_update_driver': nvidia_update_driver}), 200

    except Exception as e:
        return jsonify({"nvidia_update_driver": str(e)}), 500




@app.route('/docker_upgrade')
@token_required
def get_docker_latest():
    command = "apt list --upgradable | grep docker-ce | awk '{print $1, $2}' |tail -n 1"
    docker_upgrade = run_command(command)
    if not docker_upgrade:
        return jsonify({'docker_latest': 'Docker up to date'})
    return jsonify({'docker_latest': docker_upgrade})

@app.route('/os_latest_version')
@token_required
def search_upgrade_os_version():
    command = "apt list --upgradable |grep ubuntu- |awk '{print $1, $2}'"
    output = run_command(command).strip()
    if not output:
        return jsonify({'os_latest_version': 'OS is up to date'}), 200
    else:
        return jsonify({'os_latest_version': output}), 200   
# return jsonify({'os_latest_version': run_command(command)}), 200


@app.route('/python_latest_version')
@token_required
def search_latest_python_version():
    command = "apt list --upgradable | grep python3.1 | awk '{print $1, $2}'"
    python_latest_version = run_command(command)
    if not python_latest_version:
        return jsonify({'python_latest': 'Python is up to date'})
    return jsonify({'python_latest': python_latest_version})



############################Update the OS ###############################################
def get_upgradable_packages():
    command = "apt list --upgradable | grep ubuntu-"
    result = run_command(command)
    packages = []
    for line in result.splitlines():
        package_name = line.split('/')[0]
        packages.append(package_name)
    return packages

@app.route('/upgrade_packages', methods=['POST'])
@token_required
def upgrade_packages():
    packages = get_upgradable_packages()
    results = {}
    for package in packages:
        command = f"sudo apt-get upgrade -y"
        result = run_command(command)
        results[package] = result
    return jsonify(results)

#####################################SET HostName to Host machine #####################################################

def set_hostname(hostname):
    try:
        command = f"sudo hostnamectl set-hostname {hostname}"
        subprocess.run(command, shell=True, check=True)
        return True, f"Hostname successfully set to {hostname}"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to set hostname: {e}"

@app.route('/set_hostname' , methods=['POST'])
@token_required
def set_system_hostname():
    data = request.json
    if 'hostname' not in data:
        return jsonify({'set_hostname': 'Hostname is required'}), 400

    hostname = data['hostname']
    success, message = set_hostname(hostname)

    if success:
        return jsonify({'set_hostname': message})
    else:
        return jsonify({'set_hostname': message}), 500


#############################################Docker PULL IMAGES ########################################################

############################################RUN THE CONTAINERS ###########################################
#########################################################GET Docker images ############################################

########################upgrade python patches#######################################
@app.route('/upgrade_python3', methods=['POST'])
@token_required
def upgrade_python3():
    try:
        # Execute the command to upgrade python3 packages
        result = subprocess.run(['apt', 'list', '--upgradable'], capture_output=True, text=True, check=True)
        upgradable_packages = [line.split('/')[0] for line in result.stdout.split('\n') if 'python3' in line]

        if not upgradable_packages:
            return jsonify({"message": "No python3 packages to upgrade"}), 200

        # Perform the upgrade
        upgrade_command = ['sudo', 'apt-get', 'install', '-y'] + upgradable_packages
        subprocess.run(upgrade_command, check=True)

        return jsonify({"message": "Successfully upgraded python3 packages", "packages": upgradable_packages}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({"message": str(e)}), 500
        
        
###########ubuntu-os-upgrade ###############################
@app.route('/upgrade_ubuntu', methods=['POST'])
#@token_required
def upgrade_ubuntu():
    try:
        # Execute the command to list upgradable packages and filter for ubuntu-
        result = subprocess.run(['apt', 'list', '--upgradable'], capture_output=True, text=True, check=True)
        upgradable_packages = [line.split('/')[0] for line in result.stdout.split('\n') if 'ubuntu-' in line]

        if not upgradable_packages:
            return jsonify({"message": "No ubuntu packages to upgrade"}), 200

        # Perform the upgrade
        upgrade_command = ['sudo', 'apt-get', 'install', '-y'] + upgradable_packages
        subprocess.run(upgrade_command, check=True)

        return jsonify({"message": "Successfully upgraded ubuntu packages", "packages": upgradable_packages}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({"message": str(e)}), 500
########################################################
@app.route('/docker_latest_upgrade')
@token_required
def get_docker_latest_upgrade():
    try:
        # Execute the command to list upgradable packages and filter for docker-ce
        command = "apt list --upgradable | grep docker-ce"
        result = run_command(command)
        upgradable_packages = [line.split('/')[0] for line in result.split('\n') if 'docker-ce' in line]

        if not upgradable_packages:
            return jsonify({"message": "No Docker packages to upgrade"}), 200

        # Perform the upgrade
        upgrade_command = ['sudo', 'apt-get', 'install', '-y'] + upgradable_packages
        subprocess.run(upgrade_command, check=True)

        return jsonify({"message": "Successfully upgraded Docker packages", "packages": upgradable_packages}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500 
############################ install python3.10 to 3.11 ######################
@app.route('/install-python_3.10', methods=['POST'])
@token_required
def install_python310():
    try:
        # Check if Python 3.11 is already installed
        version_check = run_command("python3 --version")
        if "Python 3.10" in version_check:
            return jsonify({"message": "Python 3.10 is already installed"}), 200

        # List of commands to run
        commands = [
            "sudo apt update",
            #"sudo apt install python3.10 -y",
            "python3 --version",
            #"sudo apt install python3.11-dbg -y",
            #"sudo apt install python3.11-dev -y",
            #"sudo apt install python3.11-venv -y",
            #"sudo apt install python3.11-distutils -y",
            #"sudo apt install python3.11-lib2to3 -y",
            #"sudo apt install python3.11-gdbm -y",
            #"sudo apt install python3.11-tk -y",
            #"sudo apt install python3.11-full -y",
            #Set Python 3.10 as the default python3
            "sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1",
            "sudo update-alternatives --set python3 /usr/bin/python3.10",
            "sudo apt remove --purge python3-apt -y",
            "sudo apt install python3-apt -y",
            "sudo apt install software-properties-common -y",
            #"sudo pip3 install Flask==3.0.3",
            #"sudo pip3 install Flask-Cors==4.0.1",
            #"sudo pip3 install botocore==1.34.120",
            #"sudo pip3 install pymongo==4.7.2",
            #"sudo pip3 install docker==7.1.0",
            #"systemctl restart qubrid_engine1.service",
            #"systemctl restart qubrid_engine2.service"
        ]

        # Run each command
        for command in commands:
            result = run_command(command)
            if "Error" in result or "Exception" in result:
                return jsonify({"message": "Not successful", "error": result}), 500

        return jsonify({"message": "Successfully installed Python 3.10 and related packages"}), 200

    except Exception as e:
         return jsonify({"message": "Not successful", "error": str(e)}), 500

################################################################
@app.route('/install-python_3.11', methods=['POST'])
@token_required
def install_python311():
    try:
        # Check if Python 3.11 is already installed
        version_check = run_command("python3 --version")
        if "Python 3.11" in version_check:
            return jsonify({"message": "Python 3.11 is already installed"}), 200
        # List of commands to run
        commands = [
            "sudo apt update",
            "sudo apt install python3.11 -y",
            "python3.11 --version",
            "sudo apt install python3.11-dbg -y",
            "sudo apt install python3.11-dev -y",
            "sudo apt install python3.11-venv -y",
            "sudo apt install python3.11-distutils -y",
            "sudo apt install python3.11-lib2to3 -y",
            "sudo apt install python3.11-gdbm -y",
            "sudo apt install python3.11-tk -y",
            "sudo apt install python3.11-full -y",
            "sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1",
            "sudo update-alternatives --set python3 /usr/bin/python3.11",
            #"sudo update-alternatives --config python3",
            "sudo apt remove --purge python3-apt -y",
            "sudo apt install python3-apt -y",
#            "sudo apt install software-properties-common -y",
            "sudo apt install python3-pip",
            "sudo pip3 install Flask==3.0.3",
            "sudo pip3 install Flask-Cors==4.0.1",
            "sudo pip3 install botocore==1.34.120",
            "sudo pip3 install pymongo==4.7.2",
            "sudo pip3 install docker==7.1.0",
            "sudo pip3 install ping3==4.0.8",
            "sudo pip3 install apscheduler==3.10.4",
            #"systemctl restart qubrid_engine1.service",
            #"systemctl restart qubrid_engine2.service"
        ]

        # Run each command
        for command in commands:
            result = run_command(command)
            if "Error" in result or "Exception" in result:
                return jsonify({"message": "Not successful", "error": result}), 500

        return jsonify({"message": "Successfully installed Python 3.11 and related packages"}), 200

    except Exception as e:
        return jsonify({"message": "Not successful", "error": str(e)}), 500

###################################
@app.route('/install-python_3.12', methods=['POST'])
@token_required
def install_python312():
    try:
        # Check if Python 3.11 is already installed
        version_check = run_command("python3 --version")
        if "Python 3.12" in version_check:
            return jsonify({"message": "Python 3.12 is already installed"}), 200

        # List of commands to run
        commands = [
            "sudo apt update",
            "sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1",
            "sudo update-alternatives --set python3 /usr/bin/python3.10",
            "sudo apt install software-properties-common -y",
	    "sudo add-apt-repository ppa:deadsnakes/ppa -y",
            "sudo apt install python3.12 -y",
            "python3.12 --version",
            "sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1",
            "sudo update-alternatives --set python3 /usr/bin/python3.12",
            "sudo apt remove --purge python3-apt -y",
            "sudo apt install python3-apt -y",
            "sudo pip3 install Flask==3.0.3",
            "sudo pip3 install Flask-Cors==4.0.1",
            "sudo pip3 install botocore==1.34.120",
            "sudo pip3 install pymongo==4.7.2",
            "sudo pip3 install docker==7.1.0",
        ]

        # Run each command
        for command in commands:
            result = run_command(command)
            if "Error" in result or "Exception" in result:
                return jsonify({"message": "Not successful", "error": result}), 500

        return jsonify({"message": "Successfully installed Python 3.12 and related packages"}), 200

    except Exception as e:
        return jsonify({"message": "Not successful", "error": str(e)}), 500
################################ Library install #################################################################
@app.route('/library_install', methods=['POST'])
@token_required
def library_install():
    data = request.json
    if not data or 'libraries' not in data:
        return jsonify({'error': 'No libraries specified'}), 400

    libraries = data['libraries']
    results = []

    for library_name in libraries:
        try:
            result = subprocess.run(['pip3', 'install', library_name], capture_output=True, text=True)
            if result.returncode == 0:
                results.append({'message': f'Library {library_name} installed successfully'})
            else:
                results.append({'error': f'Failed to install {library_name}: {result.stderr}'})
        except Exception as e:
            results.append({'error': f'Failed to install {library_name}: {str(e)}'})

    return jsonify(results), 200
###########################LIBRARY_VERSION###################################################################
@app.route('/library_version', methods=['POST'])
@token_required
def get_library_version():
    data = request.json
    if not data or 'uid' not in data:
        return jsonify({'error': 'No library specified'}), 400

    library_uid = data['uid']

    try:
        # Run the pip3 list | grep library | awk '{print $2}' | head -n 1 command
        result = subprocess.run(
            f"pip3 list | grep {library_uid} | awk '{{print $2}}' | head -n 1",
            shell=True,
            capture_output=True,
            text=True
        )

        version = result.stdout.strip()
        if result.returncode == 0 and version:
            return jsonify({'version':version}), 200
        else:
            return jsonify({'error': f'Library {library_uid} not found or no version information available'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
#############################################################################
####################################################################

@app.route('/get-network-info', methods=['GET'])
def get_network_info():
    try:
        # Command to get network hardware information
        command = "lshw -c network | grep -E 'vendor:|product:|logical name:'"

        # Run the command and capture the output
        result = subprocess.run(
            ['bash', '-c', command],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # Split the result into lines and process each line
            output_lines = result.stdout.strip().split('\n')
            network_info = []

            buffer = {}
            for line in output_lines:
                if 'product:' in line:
                    buffer['product'] = line.split(':', 1)[1].strip()
                elif 'vendor:' in line:
                    buffer['vendor'] = line.split(':', 1)[1].strip()
                elif 'logical name:' in line:
                    logical_name = line.split(':', 1)[1].strip()
                    buffer['logical name'] = logical_name
                    network_info.append(buffer)
                    buffer = {}

            # Include the status information for each interface
            status_command = "ip a | grep state | awk '{print $2, $9}'"
            status_result = subprocess.run(
                ['bash', '-c', status_command],
                capture_output=True,
                text=True
            )

            if status_result.returncode == 0:
                status_lines = status_result.stdout.strip().split('\n')
                for status_line in status_lines:
                    parts = status_line.split()
                    if len(parts) == 2:  # Ensure the line has exactly 2 parts
                        interface_name = parts[0].strip(':')
                        interface_status = parts[1]
                        for interface in network_info:
                            if interface['logical name'] == interface_name:
                                interface['status'] = interface_status

            return jsonify(network_info), 200
        else:
            return jsonify({'error': 'Failed to retrieve network info', 'output': result.stderr}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


##############################################################################################
@app.route('/gpu-used', methods=['GET'])
def gpu_used():
    # Check if any NVIDIA GPUs are present
    gpu_presence = run_command("lspci | grep NVIDIA")
    if not gpu_presence:
        return jsonify({"message": "No GPU found"}), 404

    # Check if NVIDIA driver is installed
    driver_version = run_command("nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -n 1")
    if not driver_version:
        return jsonify({"message": "GPU driver not found"}), 404

    # Get GPU details temperature.gpu
    gpu_details = run_command("nvidia-smi --query-gpu=name,index,memory.used,memory.total,memory.free,utilization.gpu,power.draw,power.limit --format=csv,noheader")
    if not gpu_details:
        return jsonify({"message": "Failed to retrieve GPU details"}), 500

    # Parse GPU details
    gpu_info_list = []
    gpu_info_lines = gpu_details.split('\n')
    for line in gpu_info_lines:
#temperature,
        name, index, memory_used, memory_total, memory_free, utilization_gpu, power_draw, power_limit = line.split(',')
        gpu_info_list.append({
            "name": name.strip(),
            "index": index.strip(),
#            "temperature": temperature.strip(),
            "memory_used": memory_used.strip(),
            "memory_total": memory_total.strip(),
            "memory_free": memory_free.strip(),
            "utilization_gpu": utilization_gpu.strip(),
            "power_draw": power_draw.strip(),
            "power_limit": power_limit.strip()
        })

    return jsonify({"gpu_info": gpu_info_list})

@app.route('/ram-used', methods=['GET'])
def ram_used():
    # Get detailed RAM information
    ram_details = run_command("free -h")
    if not ram_details:
        return jsonify({"message": "RAM details not found"}), 404

    # Parse RAM details
    lines = ram_details.split('\n')
    values = lines[1].split()

    ram_info = {
        "total": values[1],
        "used": values[2],
        "free": values[3]
    }

    # Get used RAM percentage
    used_ram_percentage = run_command("free | awk '/^Mem/ { printf(\"%.2f\", $3/$2 * 100.0) }'")
    if used_ram_percentage:
        ram_info["used_percentage"] = f"{used_ram_percentage} %"

    return jsonify({"ram_info": ram_info})

@app.route('/disk-space', methods=['GET'])
def disk_space():
    disk_details = run_command("df -h /")
    if not disk_details:
        return jsonify({"message": "Disk space details not found"}), 404

    lines = disk_details.split('\n')
    headers = lines[0].split()
    values = lines[1].split()

    disk_info = {
        "filesystem": values[0],
        "size": values[1],
        "used": values[2],
        "available": values[3],
        "used_percentage": values[4],
        "mounted_on": values[5]
    }

    return jsonify({"disk_info": disk_info})
############################################################
LOGS_DIR = '/tmp/qubrid'
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

@app.route('/pull_docker', methods=['POST'])
def pull_docker():
    image_name = request.json.get('image_name')
    if not image_name:
        return jsonify({"error": "No image name provided"}), 400

    log_file_path = os.path.join(LOGS_DIR, f'{image_name.replace("/", "_").replace(":", "_")}_pull.log')

    try:
        # Pull the Docker image and save logs to a file
        result = subprocess.run(['docker', 'pull', image_name], capture_output=True, text=True)
        with open(log_file_path, 'w') as log_file:
            log_file.write(result.stdout)
            if result.returncode != 0:
                log_file.write(result.stderr)
                raise Exception(result.stderr)
        host_ip = socket.gethostbyname(socket.gethostname())
        return jsonify({"message": f"Successfully pulled {image_name} on host {host_ip}", "log_file": log_file_path}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download_logs/<filename>', methods=['GET'])
def download_logs(filename):
    log_file_path = os.path.join(LOGS_DIR, filename)
    if os.path.isfile(log_file_path):
        return send_file(log_file_path, as_attachment=True)
    return jsonify({"error": "Log file not found"}), 404
##############################
def get_docker_images():
    try:
        # Run the 'docker images' command with a specific format to get Docker images
        result = subprocess.run(
            ["sudo", "docker", "images", "--format", "{{.Repository}}:{{.Tag}} {{.ID}} {{.CreatedSince}} {{.Size}}"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        images = result.stdout.decode().strip().split('\n')
        images_list = []
        for image in images:
            parts = image.split()

            # Ensure the parts list has the expected length
            if len(parts) < 6:
                continue  # Skip this line if it doesn't have enough parts

            repo_tag = parts[0]
            img_id = parts[1]
            created = ' '.join(parts[2:5])  # Capture "CreatedSince" with potential multi-word value
            size = parts[5]

            # Ensure repo_tag can be split into repo and tag
            if ':' not in repo_tag:
                continue  # Skip if repo_tag doesn't contain a colon

            repo, tag = repo_tag.split(":")

            # Append to images list
            images_list.append({
                "repository": repo,
                "tag": tag,
                "image_id": img_id,
                "created": created,
                "size": size
            })
        return images_list
    except subprocess.CalledProcessError as e:
        return []

@app.route('/docker-images', methods=['GET'])
def docker_images():
    images = get_docker_images()
    return jsonify(images), 200
###################################################Docker Remove  Images  #####################################

@app.route('/remove_image', methods=['POST'])
@token_required
def remove_image():
    data = request.get_json()
    image_id = data.get('image_id')
    
    if not image_id:
        return jsonify({"error": "image_id is required"}), 400
    
    try:
        # Run the Docker rmi command
        result = subprocess.run(['docker', 'rmi', '-f', image_id], capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({"status": "success", "message": f"Image {image_id} removed successfully"})
        else:
            return jsonify({"status": "failure", "message": result.stderr.strip()}), 500
    except Exception as e:
        return jsonify({"status": "failure", "message": str(e)}), 500

#############################################################################
def get_local_ip():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    return local_ip

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def generate_random_port():
    while True:
        port = random.randint(4000, 5000)
        if not is_port_in_use(port):
            return port

@app.route('/run_gpu_docker', methods=['POST'])
#@token_required
def run_docker():
    try:
        # Get the local IP address
        local_ip = get_local_ip()

        # Get the required inputs from the POST request
        data = request.json
        user_name = data.get("user_name")
        image_name = data.get("image_name")
        gpus = data.get("gpus")  # No default value here
       # port = data.get("port")
        jupyter_pass = data.get("jupyter_pass")

        # Validate input
        if not all([user_name, image_name, jupyter_pass]):
            return jsonify({"message": "Missing required parameter(s)"}), 400

        port = generate_random_port()

        log_file_path = f"/tmp/qubrid/docker_{user_name}.log"
        os.makedirs("/tmp/qubrid", exist_ok=True)
        # Build the Docker run command
        docker_run_command = [
            "sudo", "docker", "run", "-it", "-d",
            "-v", f"/flash/home/{user_name}:/workspace/",
            "-p", f"{port}:8888", "--name", user_name, image_name, "bash"
        ]

        # Add the GPU option if specified
        if gpus:
            docker_run_command.insert(4, f"--gpus={gpus}")

        docker_exec_command = [
            "sudo", "docker", "exec", "-d", user_name,
            "jupyter", "lab", "--allow-root", "--ip=0.0.0.0", f"--NotebookApp.token={jupyter_pass}"
        ]

        # Run the Docker run command and save logs
        with open(log_file_path, 'a') as log_file:
            subprocess.run(docker_run_command, check=True, stdout=log_file, stderr=log_file)

        # Run the Docker exec command and save logs
        with open(log_file_path, 'a') as log_file:
            subprocess.run(docker_exec_command, check=True, stdout=log_file, stderr=log_file)

        # Run the Docker run command
#        subprocess.run(docker_run_command, check=True)

        # Run the Docker exec command
 #       subprocess.run(docker_exec_command, check=True)

        # Print the Jupyter Lab URL
        jupyter_url = f"http://{local_ip}:{port}"
        return jsonify({"message": f"Access Jupyter Lab at: {jupyter_url} And jupyter token is: {jupyter_pass} and Logs are the save on /tmp/qubrid"}), 200
    except subprocess.CalledProcessError:
        return jsonify({"message": "Failed to start Jupyter Lab. Please check the container image again."}), 500

    except Exception as e:
        return jsonify({"message": str(e)}), 500
###########################################################################
def get_docker_ps_output():
    try:
        result = subprocess.run(
            ['docker', 'ps', '-a', '--format', '{{json .}}'], 
            capture_output=True, text=True, check=True
        )
        containers = []
        for line in result.stdout.splitlines():
            container = eval(line)  # Parse JSON object
            # Extract only the required fields
            filtered_container = {
                'status': container.get('Status'),
                'state': container.get('State'),
                'ports': container.get('Ports'),
                'names': container.get('Names'),
                'image': container.get('Image'),
                'containerid': container.get('ID')
            }
            containers.append(filtered_container)
        return containers
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        return []
@app.route('/docker-containers', methods=['GET'])
def list_docker_containers():
    containers = get_docker_ps_output()
    return jsonify(containers)
#################################
def handle_docker_container(action, container_name):
    try:
        # Select the appropriate docker command based on the action
        if action == "start":
            command = ["sudo", "docker", "start", container_name]
        elif action == "remove":
            command = ["sudo", "docker", "rm","-f", container_name]
        elif action == "stop":
            command = ["sudo", "docker", "stop", container_name]
        else:
            return {"error": "Invalid action specified."}

        # Run the selected docker command
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return {"message": f"Container '{container_name}' {action} successfully."}
    except subprocess.CalledProcessError as e:
        return {"error": e.stderr.decode().strip()}

@app.route('/docker-container', methods=['POST'])
def docker_container():
    # Get the action and container name from the JSON request body
    data = request.get_json()
    action = data.get("action")
    container_name = data.get("name")

    if not action or not container_name:
        return jsonify({"error": "Action and container name are required"}), 400

    result = handle_docker_container(action, container_name)

    if "error" in result:
        return jsonify(result), 500
    return jsonify(result), 200



#######################################
if __name__ == "__main__":
    app.run(host='0.0.0.0' , debug=True)
    #app.run(host='0.0.0.0')
