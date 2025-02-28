import os
import subprocess
import sys

# pasta_vpn = "/app/vpn/udp"
pasta_vpn = "openvpn/tcp"
def get_vpn_file(numero):
    arquivos = [arq for arq in os.listdir(pasta_vpn) if arq.endswith(".ovpn")]
    arquivos.sort()

    if 1 <= numero <= len(arquivos):
        return arquivos[numero - 1]
    else:
        print(f"O número {numero} está fora do intervalo de arquivos disponíveis.")
        return None


numero = int(sys.argv[1])
vpn_config = get_vpn_file(numero)
print('vpn_config:',vpn_config)

script_path = "ativar_vpn.sh"

command = [script_path, vpn_config]

subprocess.run(command)
