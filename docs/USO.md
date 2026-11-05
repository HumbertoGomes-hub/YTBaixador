# Como usar

## Pela página do vídeo

Em qualquer vídeo (`youtube.com/watch?v=…`) aparece o botão **Baixar** ao lado de Curtir/Compartilhar.

1. Clique em **Baixar** e escolha o formato.
2. O botão mostra a porcentagem enquanto baixa (a barra de fundo enche), depois **Processando…** enquanto o ffmpeg junta ou converte o arquivo.
3. Ao terminar, aparece uma notificação do sistema. Clique nela para abrir a pasta.

Nos **Shorts** o botão aparece flutuando no canto inferior direito.

## Pelo popup

Clique no ícone da extensão na barra do navegador.

- **Vídeo atual**: miniatura, título, canal, duração e a resolução máxima disponível. Resoluções que o vídeo não tem ficam desativadas.
- **Formato + Baixar**: o formato escolhido fica salvo como padrão.
- **Downloads**: os últimos 30, com barra de progresso, velocidade e tempo restante.
  - **Cancelar**: interrompe o download em andamento.
  - **Abrir pasta**: abre a pasta do arquivo no gerenciador de arquivos.
  - **Tentar de novo**: aparece em downloads com erro ou cancelados.
  - **✕**: tira o item da lista (o arquivo continua no disco).
  - **Limpar concluídos**: tira da lista tudo que não está em andamento.
- **⚙ Configurações**:
  - **Pasta de destino**: caminho absoluto ou com `~` (ex.: `~/Vídeos/YouTube`). A pasta é criada se não existir. Vazio = pasta Downloads do sistema.
  - **Abrir pasta**: abre a pasta de destino.
  - **Atualizar yt-dlp**: baixa a versão mais nova do yt-dlp. Faça isso quando os downloads começarem a falhar.
  - A linha de baixo mostra o que o host encontrou: versão do yt-dlp, ffmpeg e runtime JavaScript.

## Formatos

| Opção | Resultado | Observação |
|---|---|---|
| Vídeo · melhor qualidade | melhor vídeo + melhor áudio | MP4 quando os codecs permitem; senão **MKV** (comum em 4K/AV1/VP9 com Opus) |
| Vídeo · 1080p / 720p / 480p | até essa resolução, em MP4 | prefere H.264 + AAC, que abre em qualquer player e editor |
| Áudio · MP3 | MP3 na melhor qualidade VBR | com capa e metadados (título, artista) |
| Áudio · M4A | AAC em M4A | geralmente sem reconversão, com capa e metadados |

Se você precisa de um arquivo que abra em qualquer lugar (TV, celular, editor de vídeo), escolha 1080p ou 720p.

## Nome dos arquivos

`Título do vídeo [ID].ext`, por exemplo `Me at the zoo [jNQXAC9IVRw].mp4`. O ID evita que dois vídeos com o mesmo título se sobrescrevam.

## Playlists

Só o vídeo aberto é baixado, mesmo que a URL tenha `&list=…`. A playlist inteira não é baixada.
