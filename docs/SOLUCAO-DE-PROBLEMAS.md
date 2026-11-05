# Solução de problemas

Primeiro, abra o popup → ⚙ e veja a linha de status do host. Ela mostra o que está faltando.

## "Native host não instalado" / "Specified native messaging host not found"

O navegador não achou o registro do host.

1. Rode `./host/install.sh` e confira se aparece `✓ Registrado em …` para o seu navegador.
2. **Reinicie o navegador por completo**: feche todas as janelas e, no Linux, confira se não ficou processo em segundo plano.
3. Confira se o arquivo existe, por exemplo no Brave:
   ```bash
   cat ~/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts/com.ytbaixador.host.json
   ```
   O `path` deve apontar para um `ytdl_host.py` que existe e é executável.
4. Se o navegador usa um perfil fora de `~/.config` (Flatpak ou Snap), veja a seção [Flatpak e Snap](#flatpak-e-snap).

## "Access to the specified native messaging host is forbidden"

O ID da extensão carregada não é o que o host permite. Em geral, a extensão foi carregada de uma pasta diferente de `~/.local/share/yt-baixador/extension`: por exemplo, da pasta extraída do pacote, cujo manifest não tem a chave da sua instalação. Remova a extensão e carregue-a de `~/.local/share/yt-baixador/extension`. Se você usa outro ID de propósito (modo `--dev`), rode:

```bash
EXT_ID=seu_id_aqui ./host/install.sh
```

## "Native host has exited" / o host fecha logo depois de abrir

Veja o log do host:

```bash
tail -50 ~/.local/share/yt-baixador/host.log
```

No modo `--dev`, o log fica em `host/host.log`. Causas comuns: `python3` fora do `PATH` do navegador ou falta de permissão de execução (`chmod +x ytdl_host.py`).

## Erros do YouTube durante o download

| Mensagem | Causa | Solução |
|---|---|---|
| `The page needs to be reloaded` | yt-dlp desatualizado | ⚙ → **Atualizar yt-dlp** |
| `Sign in to confirm you're not a bot` | o YouTube bloqueou temporariamente seu IP | espere um pouco; atualize o yt-dlp; evite muitos downloads seguidos |
| `n challenge solving failed` / `No supported JavaScript runtime` | falta deno/node | `./host/install.sh --update-tools` |
| `Requested format is not available` | o vídeo não tem esse formato | escolha "melhor qualidade" |
| `Video unavailable` / `Private video` | vídeo privado, removido ou bloqueado na região | — |
| `Sign in to confirm your age` | vídeo com restrição de idade | não é suportado (exigiria passar cookies ao yt-dlp) |

## O arquivo baixou, mas não tem som, ou vieram dois arquivos separados

O ffmpeg não está instalado. Instale com `sudo apt install ffmpeg` e baixe de novo.

## O vídeo saiu em MKV / não abre no meu player

A opção "melhor qualidade" usa MKV quando os codecs (AV1, VP9, Opus) não cabem em MP4. Use **1080p** ou **720p**, que geram MP4 com H.264 + AAC.

## O botão "Baixar" não aparece na página

- Recarregue a página do YouTube (F5). Abas que já estavam abertas antes de instalar ou recarregar a extensão não recebem o script.
- O YouTube muda o layout com frequência. Se ele não achar a barra de ações, o botão aparece flutuando no canto inferior direito. Se nem isso aparecer, use o popup e abra uma issue com a URL.

## "Acompanhamento perdido"

O navegador foi fechado ou a extensão foi recarregada no meio de um download. O download em si continua até o fim, mas a extensão não recebe mais o progresso. Confira a pasta de destino.

## Flatpak e Snap

Navegadores em sandbox não enxergam o host registrado em `~/.config`, e às vezes nem conseguem executar programas de fora. Use a versão `.deb`/`.rpm` do navegador ou registre o host manualmente na pasta de configuração do sandbox (ex.: `~/.var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser/NativeMessagingHosts/`). Mesmo assim, a sandbox pode impedir a execução.

## Ver o que está acontecendo

- **Log do host**: `~/.local/share/yt-baixador/host.log` (ou `host/host.log` no modo dev). Mostra o comando exato do yt-dlp e o erro.
- **Console do service worker**: `chrome://extensions` → YT Baixador → *service worker* → aba Console.
- **Teste do host sem o navegador**:
  ```bash
  python3 scripts/test_host.py --host ~/.local/share/yt-baixador/ytdl_host.py --online
  ```
