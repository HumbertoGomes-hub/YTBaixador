# Instalação

O YT Baixador tem duas partes, e as duas precisam ser instaladas:

1. **Native host**: um programa em Python que roda o yt-dlp no seu computador. Ele é instalado pelo `host/install.sh`.
2. **Extensão**: a parte que aparece no navegador. Ela é carregada pela página de extensões.

## Requisitos

| Item | Por quê | Como instalar (Debian/Ubuntu) |
|---|---|---|
| Linux x86_64 ou aarch64 | o instalador e os binários são para Linux | — |
| Python 3.8+ | roda o native host | já vem no sistema |
| ffmpeg | junta vídeo e áudio e converte para MP3/M4A | `sudo apt install ffmpeg` |
| curl | o instalador baixa o yt-dlp e o deno | `sudo apt install curl` |
| Navegador Chromium | Chrome, Chromium, Brave, Edge ou Vivaldi | — |

O instalador baixa sozinho os outros dois componentes:

- **yt-dlp**: a versão mais recente, de `github.com/yt-dlp/yt-dlp/releases`. Não use o do `apt`, porque ele costuma estar velho demais para o YouTube.
- **deno**: de `github.com/denoland/deno/releases`. O yt-dlp precisa de um runtime JavaScript para resolver os desafios do YouTube. Se você já tem `deno` ou `node` no sistema, ele não é baixado.

## 1. Instalar o native host

A partir do pacote de release:

```bash
tar xzf yt-baixador-1.0.0-linux.tar.gz
```

```bash
cd yt-baixador-1.0.0 && ./host/install.sh
```

O que o instalador faz:

1. Copia `ytdl_host.py` para `~/.local/share/yt-baixador/`.
2. Baixa `yt-dlp` e `deno` para `~/.local/share/yt-baixador/bin/`.
3. Cria o arquivo `com.ytbaixador.host.json` na pasta `NativeMessagingHosts` de cada navegador que encontrar em `~/.config`. Esse arquivo diz ao navegador onde está o host e qual extensão pode usá-lo.

Ele também copia a extensão para `~/.local/share/yt-baixador/extension/` e gera para ela um **ID exclusivo desta instalação**. Esse ID é guardado em `manifest-key.txt` e reaproveitado nas atualizações. Depois disso, a pasta extraída pode ser apagada.

### Opções do instalador

| Opção | Efeito |
|---|---|
| *(nenhuma)* | instalação normal em `~/.local/share/yt-baixador` |
| `--no-download` | não baixa yt-dlp/deno; usa os que estiverem no `PATH` |
| `--update-tools` | baixa de novo o yt-dlp e o deno |
| `--dev` | registra o host direto da pasta do projeto (para desenvolvimento; exige `EXT_ID`) |
| `--uninstall` | remove o registro e a pasta instalada |
| `PREFIX=/outra/pasta` | instala em outra pasta |
| `EXT_ID=...` | libera esse ID de extensão em vez do gerado pela instalação |

## 2. Carregar a extensão

1. Abra a página de extensões do navegador:
   - Chrome / Chromium: `chrome://extensions`
   - Brave: `brave://extensions`
   - Edge: `edge://extensions`
   - Vivaldi: `vivaldi://extensions`
2. Ative o **Modo do desenvolvedor**.
3. Clique em **Carregar sem compactação** e escolha a pasta `~/.local/share/yt-baixador/extension` (no seletor de arquivos, `Ctrl+H` mostra pastas ocultas como `.local`).
4. Confira se o ID no card da extensão é o mesmo que o instalador mostrou no final. É esse ID que o host aceita.
5. **Reinicie o navegador** na primeira instalação, para ele ler o registro do host.
6. Fixe o ícone da extensão na barra (ícone de quebra-cabeça → alfinete).

Para conferir, abra o popup da extensão e clique em ⚙. A linha de baixo deve mostrar a versão do yt-dlp, `ffmpeg ok` e `JS deno` (ou `node`).

## Atualizar

- **Só o yt-dlp** (o mais comum, quando o YouTube muda): no popup, ⚙ → **Atualizar yt-dlp**. Também dá para rodar `./host/install.sh --update-tools`.
- **Nova versão do YT Baixador**: extraia o pacote novo e rode `./host/install.sh`. Ele atualiza o host e a extensão em `~/.local/share/yt-baixador`, mantendo o mesmo ID. Depois clique em ↻ (recarregar) no card da extensão em `chrome://extensions`. Suas configurações e a lista de downloads continuam.

## Desinstalar

1. Remova a extensão em `chrome://extensions`.
2. Rode o desinstalador:

```bash
./host/install.sh --uninstall
```

Ele apaga os registros do host em todos os navegadores e a pasta `~/.local/share/yt-baixador`. Os vídeos baixados não são tocados.

## Outros sistemas

- **Firefox**: não é suportado ainda. Precisaria de um manifest com `browser_specific_settings`, do registro do host em `~/.mozilla/native-messaging-hosts/` e de `allowed_extensions` no lugar de `allowed_origins`.
- **Windows e macOS**: o host em Python funciona, mas o registro é diferente (chave no registro do Windows; `~/Library/Application Support/<navegador>/NativeMessagingHosts` no macOS) e o `install.sh` não cobre esses casos.
