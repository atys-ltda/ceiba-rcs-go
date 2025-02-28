#!/bin/bash

USUARIO="ncpjosergm86@namecheap"
SENHA="vYni9US6Ms"

DIRETORIO_OVPN="openvpn/tcp"

ARQUIVO_OVPN="$1"


CAMINHO_COMPLETO="${DIRETORIO_OVPN}/${ARQUIVO_OVPN}"

if [ -z "$ARQUIVO_OVPN" ]; then
    echo "Nenhum arquivo .ovpn encontrado no diretório $DIRETORIO_OVPN"
    CAMINHO_COMPLETO=$(find "$DIRETORIO_OVPN" -type f -name "*.ovpn" | shuf -n 1)
fi

pkill openvpn

printf "%s\n%s\n" "$USUARIO" "$SENHA" | openvpn --config "$CAMINHO_COMPLETO" --auth-user-pass /dev/stdin > /dev/null 2>&1 &
