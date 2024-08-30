from flask import Flask, jsonify,request,session
import subprocess
import jwt
from functools import wraps
from flask_cors import CORS
import socket
import docker
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
@app.route('/cpu_info')
def get_cpu_info():
    command = "lscpu |grep Core |awk '{print $4}'"
    return jsonify({'cpu_info': run_command(command)})

@app.route('/ram_info')
def get_ram_size():
    command = "free -h |grep 'Mem' | awk '{print $2}'"
    return jsonify({'ram_info': run_command(command)})
#############################################################
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

if __name__ == "__main__":
    app.run(host='0.0.0.0' , debug=True)
    #app.run(host='0.0.0.0')
