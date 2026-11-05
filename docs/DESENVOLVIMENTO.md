# Desenvolvimento

## Preparar o ambiente

1. Carregue `extension/` direto do projeto em `chrome://extensions` → **Carregar sem compactação**. Sem `key` no manifest, o navegador dá a ela um ID baseado no caminho da pasta.
2. Copie o ID mostrado no card da extensão e registre o host com ele:
   ```bash
   EXT_ID=<id copiado> ./host/install.sh --dev
   ```

O modo `--dev` registra `host/ytdl_host.py` direto da pasta do projeto e baixa o yt-dlp e o deno para `host/bin/`. Assim, mudanças no host e na extensão valem sem reinstalar. O ID só muda se você mover a pasta do projeto; nesse caso, repita o passo 2.

> **Não coloque `key` no `extension/manifest.json` do repositório.** O ID de cada usuário é gerado pelo instalador, e o `check.py` falha se encontrar uma `key`.

> Para voltar ao modo normal, rode `./host/install.sh` sem `--dev`. Os dois modos sobrescrevem o mesmo registro: o host passa a aceitar só o ID da cópia instalada em `~/.local/share/yt-baixador/extension`.

## Ciclo de trabalho

| Mudou… | Faça |
|---|---|
| `background.js` ou `manifest.json` | ↻ no card da extensão em `chrome://extensions` |
| `content.js` / `content.css` | ↻ na extensão **e** F5 na aba do YouTube |
| `popup.*` | feche e abra o popup (para `manifest.json`, ↻ na extensão) |
| `host/ytdl_host.py` | ↻ na extensão (a conexão com o host é refeita) |

Onde ver os logs:
- **Service worker**: `chrome://extensions` → YT Baixador → link *service worker* → Console.
- **Popup**: clique direito no popup → Inspecionar.
- **Content script**: DevTools da aba do YouTube → Console (contexto "YT Baixador").
- **Host**: `tail -f host/host.log`.

## Testes

```bash
python3 scripts/check.py
```

```bash
python3 scripts/test_host.py
```

```bash
python3 scripts/test_host.py --online
```

- `check.py`: valida o manifest, os arquivos que ele referencia, a versão igual na extensão e no host, a seção no CHANGELOG, a sintaxe de Python e shell e roda o `deno lint` (ou `node --check`) no JavaScript.
- `test_host.py`: abre o host como o navegador faz e testa `ping` e um download de um MP4 gerado com ffmpeg e servido em `127.0.0.1`. Funciona sem internet.
- `test_host.py --online`: também testa `info` e downloads `720` e `mp3` de um vídeo curto do YouTube. Use depois de atualizar o yt-dlp ou mexer nos presets.
- `--host CAMINHO`: testa outra cópia do host, por exemplo a instalada em `~/.local/share/yt-baixador/ytdl_host.py`.

A interface (botão e popup) é testada à mão. Roteiro mínimo antes de um release:

1. Vídeo normal: botão aparece; baixar em 720p; progresso no botão e no popup; notificação; "Abrir pasta".
2. Baixar em "melhor qualidade" (duas partes + junção) e em MP3.
3. Cancelar um download longo.
4. Navegar para outro vídeo sem recarregar a página: o botão continua lá.
5. Shorts: botão flutuante.
6. Mudar a pasta de destino nas configurações e baixar.
7. Com o host desinstalado (`./host/install.sh --uninstall`), o popup mostra o aviso de instalação.

## Receitas

### Adicionar um formato (preset)

1. `host/ytdl_host.py` → dicionário `PRESETS`: adicione a chave com os argumentos do yt-dlp.
2. `extension/popup.html` → `<select id="preset">`: adicione a `<option>`.
3. `extension/content.js` → lista `PRESETS`: adicione o par `[chave, rótulo]`.
4. `extension/popup.js` → `PRESET_LABELS`.
5. Documente em [USO.md](USO.md#formatos) e [ARQUITETURA.md](ARQUITETURA.md#presets--argumentos-do-yt-dlp).

### Adicionar um comando ao host

1. Crie `cmd_xxx(msg)` em `ytdl_host.py` e registre em `COMMANDS`. Comandos demorados devem rodar em uma thread, para não travar a leitura do stdin.
2. Se tiver resposta, inclua `reqId` e chame `request({ cmd: "xxx" })` no `background.js`. A promise resolve com a mensagem que tiver o mesmo `reqId`.
3. Documente na tabela do protocolo em [ARQUITETURA.md](ARQUITETURA.md#protocolo-do-native-host).

### O botão sumiu depois de uma mudança do YouTube

Abra o DevTools no YouTube, ache o contêiner dos botões Curtir/Compartilhar e atualize a lista `ANCHORS` em `content.js`. O primeiro seletor que existir é usado; o botão é inserido antes dele.

### Trocar o ícone

Edite as formas em `scripts/gen_icons.py` e rode `python3 scripts/gen_icons.py`.

## Convenções

- Interface e mensagens ao usuário em português (pt-BR).
- Sem dependências externas: a extensão é JS puro, sem bundler; o host e os scripts usam só a biblioteca padrão do Python.
- A versão fica em dois lugares (`manifest.json` e `HOST_VERSION`). Mude sempre com `scripts/bump_version.py`.
