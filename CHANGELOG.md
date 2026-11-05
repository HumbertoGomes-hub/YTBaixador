# Changelog

Todas as mudanças relevantes deste projeto. O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e as versões seguem o [SemVer](https://semver.org/lang/pt-BR/).

## [1.0.0] - 2026-11-05

### Adicionado

- Extensão Manifest V3 para Chrome, Chromium, Brave, Edge e Vivaldi, com ID gerado em cada instalação (nenhuma chave do autor).
- Botão **Baixar** na página do vídeo, com menu de formatos e progresso no próprio botão; botão flutuante nos Shorts.
- Popup com o vídeo atual (miniatura, canal, duração, resolução máxima), fila de downloads, cancelar, tentar de novo, abrir pasta e limpar concluídos.
- Formatos: melhor qualidade (MP4/MKV), 1080p, 720p e 480p em MP4 (H.264 + AAC), MP3 e M4A com capa e metadados.
- Configurações: pasta de destino e formato padrão.
- Notificação ao terminar ou falhar um download.
- Native host em Python (só biblioteca padrão) que roda o yt-dlp, com progresso por partes, cancelamento e atualização do yt-dlp pelo popup.
- Instalador `host/install.sh`: copia extensão e host para `~/.local/share/yt-baixador`, gera o ID da extensão localmente, modo `--dev`, `--update-tools` e `--uninstall`; baixa o yt-dlp e o deno oficiais.
- Scripts `check.py` (com verificação de segredos e dados locais), `test_host.py`, `build.py`, `bump_version.py` e `gen_icons.py`.
- Documentação de instalação, uso, solução de problemas, arquitetura, desenvolvimento e deploy.
- Licença Apache 2.0.
