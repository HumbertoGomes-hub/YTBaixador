# YT Baixador

Extensão para navegadores Chromium (Chrome, Brave, Edge, Vivaldi, Chromium) que baixa vídeos e áudios do YouTube direto da página do vídeo, usando o [yt-dlp](https://github.com/yt-dlp/yt-dlp) instalado no seu computador.

- Botão **Baixar** ao lado de Curtir/Compartilhar, com progresso no próprio botão
- Formatos: melhor qualidade, 1080p, 720p, 480p (MP4), MP3 e M4A (com capa e metadados)
- Popup com o vídeo atual, a fila de downloads, cancelar, tentar de novo e abrir a pasta
- Notificação ao terminar; pasta de destino configurável
- Funciona também nos Shorts (botão flutuante)

> Use apenas para conteúdo que você tem direito de baixar. Baixar vídeos vai contra os Termos de Serviço do YouTube, e as lojas de extensões não aceitam esse tipo de extensão. Por isso ela é distribuída como pacote para instalação manual.

## Instalação rápida

Requisitos: Linux, Python 3, `curl` e `ffmpeg` (`sudo apt install ffmpeg curl`).

```bash
tar xzf yt-baixador-1.0.0-linux.tar.gz
```

```bash
cd yt-baixador-1.0.0 && ./host/install.sh
```

O instalador copia tudo para `~/.local/share/yt-baixador` e mostra no final qual pasta carregar. Abra `chrome://extensions` (ou `brave://extensions`, `edge://extensions`…), ative o **Modo do desenvolvedor**, clique em **Carregar sem compactação**, escolha `~/.local/share/yt-baixador/extension` e reinicie o navegador. Depois disso, a pasta extraída pode ser apagada.

O passo a passo completo está em [docs/INSTALACAO.md](docs/INSTALACAO.md).

## Documentação

| Documento | Para quem | Conteúdo |
|---|---|---|
| [INSTALACAO.md](docs/INSTALACAO.md) | usuário | requisitos, instalação, atualização e desinstalação |
| [USO.md](docs/USO.md) | usuário | botão, popup, formatos e configurações |
| [SOLUCAO-DE-PROBLEMAS.md](docs/SOLUCAO-DE-PROBLEMAS.md) | usuário | erros comuns e como resolver |
| [ARQUITETURA.md](docs/ARQUITETURA.md) | desenvolvedor | componentes, protocolo do native host e estado |
| [DESENVOLVIMENTO.md](docs/DESENVOLVIMENTO.md) | desenvolvedor | ambiente, testes e como estender |
| [DEPLOY.md](docs/DEPLOY.md) | mantenedor | como gerar e publicar um release |
| [CHANGELOG.md](CHANGELOG.md) | todos | histórico de versões |

## Estrutura do projeto

```
YTBaixador/
├── extension/              extensão (Manifest V3)
│   ├── manifest.json       sem "key": cada instalação gera o próprio ID
│   ├── background.js       service worker: fala com o native host e guarda o estado
│   ├── content.js/.css     botão "Baixar" injetado no YouTube
│   ├── popup.html/.css/.js janela da extensão
│   └── icons/              gerados por scripts/gen_icons.py
├── host/
│   ├── ytdl_host.py        native host (Python, só biblioteca padrão) que roda o yt-dlp
│   ├── install.sh          instala/registra o host nos navegadores
│   └── bin/                yt-dlp e deno no modo --dev (ignorado pelo git)
├── scripts/                check, build, testes, versão e ícones
├── docs/                   documentação
├── dist/                   pacotes gerados pelo build (ignorado pelo git)
├── CHANGELOG.md            histórico de versões
└── LICENSE                 Apache License 2.0
```

## Independente de quem publica

Tudo roda na máquina de quem instala, e nada depende do autor nem passa por ele:

- **Sem servidor**: o native host é um processo local que o navegador abre e fecha. Ele conversa pela entrada e saída padrão e não abre nenhuma porta.
- **Sem chave do autor**: o `install.sh` gera um ID de extensão aleatório e exclusivo em cada instalação. Não existe chave privada para guardar nem para vazar.
- **Sem telemetria**: as únicas conexões de rede são do yt-dlp com o YouTube e, durante a instalação, os downloads do yt-dlp e do deno nos releases oficiais deles no GitHub.

## Comandos

| Comando | O que faz |
|---|---|
| `./host/install.sh` | instala o host em `~/.local/share/yt-baixador` e registra nos navegadores |
| `EXT_ID=<id> ./host/install.sh --dev` | registra o host direto da pasta do projeto (desenvolvimento) |
| `./host/install.sh --uninstall` | remove o host |
| `python3 scripts/check.py` | verificações estáticas (manifest, versões, sintaxe, lint) |
| `python3 scripts/test_host.py [--online]` | teste de ponta a ponta do native host |
| `python3 scripts/build.py` | gera os pacotes de release em `dist/` |
| `python3 scripts/bump_version.py X.Y.Z` | muda a versão da extensão e do host |
| `python3 scripts/gen_icons.py` | gera os ícones de novo |
