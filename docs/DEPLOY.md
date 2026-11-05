# Deploy e releases

## Como o YT Baixador é distribuído

A Chrome Web Store e a loja de complementos do Edge **não aceitam** extensões que baixam vídeos do YouTube. Por isso o projeto é distribuído como um pacote que o usuário instala manualmente, publicado na página de **Releases** do GitHub:

| Artefato | Conteúdo | Para quê |
|---|---|---|
| `yt-baixador-X.Y.Z-linux.tar.gz` | `extension/`, `host/ytdl_host.py`, `host/install.sh`, `README.md`, `CHANGELOG.md`, `docs/` | pacote principal para o usuário final |
| `SHA256SUMS` | checksum do pacote | conferir a integridade do download |

O yt-dlp e o deno **não** entram no pacote nem no repositório. O `install.sh` baixa as versões mais recentes na máquina do usuário, o que deixa o pacote pequeno e evita entregar um yt-dlp que já nasce desatualizado.

## O que vai (e o que não vai) para o repositório

| Vai para o git | Fica fora (`.gitignore`) |
|---|---|
| `extension/`, `host/ytdl_host.py`, `host/install.sh`, `scripts/`, `docs/`, `README.md`, `CHANGELOG.md`, `LICENSE`, `.gitignore` | `dist/` (vai para Releases), `host/bin/` (binários), `host/host.log`, `*.pem`, `*.key`, `keys/` |

> **Envie sempre com `git push`, nunca arrastando a pasta para o site do GitHub.** O upload pelo navegador ignora o `.gitignore` e envia tudo: binários, logs com o seu usuário e caminhos e, se estiver na pasta, a chave privada. Além disso, ele costuma pular arquivos que começam com ponto, como o próprio `.gitignore`.

O `scripts/check.py` falha se encontrar chaves privadas, logs ou caminhos `/home/<usuário>` em arquivos do projeto. Rode-o antes de cada commit.

## Checklist de release

1. **Atualize a versão** (segue [SemVer](https://semver.org/lang/pt-BR/)):
   ```bash
   python3 scripts/bump_version.py 1.1.0
   ```
   Isso muda `extension/manifest.json`, `HOST_VERSION` em `host/ytdl_host.py` e cria a seção no `CHANGELOG.md`.
2. **Preencha o `CHANGELOG.md`** com o que mudou e apague os subtítulos vazios.
3. **Rode as verificações**:
   ```bash
   python3 scripts/check.py
   ```
   ```bash
   python3 scripts/test_host.py --online
   ```
4. **Teste a interface** seguindo o roteiro em [DESENVOLVIMENTO.md](DESENVOLVIMENTO.md#testes), de preferência em uma instalação limpa:
   ```bash
   ./host/install.sh --uninstall && ./host/install.sh
   ```
5. **Gere os pacotes** (roda o `check.py` antes):
   ```bash
   python3 scripts/build.py
   ```
   Os arquivos ficam em `dist/`.
6. **Teste o pacote gerado**: extraia o `.tar.gz` numa pasta temporária, rode `./host/install.sh`, carregue `~/.local/share/yt-baixador/extension` e baixe um vídeo.
7. **Faça o commit, crie a tag e envie**:
   ```bash
   git commit -am "Versão 1.1.0"
   ```
   ```bash
   git tag -a v1.1.0 -m "YT Baixador 1.1.0"
   ```
   ```bash
   git push origin main v1.1.0
   ```
8. **Publique o release**: no GitHub, abra **Releases → Draft a new release**, escolha a tag `v1.1.0`, cole a seção do CHANGELOG e anexe os dois arquivos de `dist/`. Com o [GitHub CLI](https://cli.github.com/), o mesmo passo fica assim:
   ```bash
   gh release create v1.1.0 dist/yt-baixador-1.1.0-linux.tar.gz dist/SHA256SUMS --title "YT Baixador 1.1.0" --notes-file <(sed -n '/## \[1.1.0\]/,/## \[/p' CHANGELOG.md | sed '$d')
   ```

## ID da extensão (sem chave do autor)

O `extension/manifest.json` do repositório **não tem** o campo `key`, e nenhum mantenedor guarda chave privada. Cada instalação gera o próprio ID:

- Na primeira execução, o `install.sh` cria uma chave RSA, guarda **só a parte pública** em `~/.local/share/yt-baixador/manifest-key.txt` e grava essa chave no `manifest.json` da cópia instalada da extensão. A parte privada é descartada na hora.
- Nas atualizações, a mesma chave é reaproveitada, então o ID e os dados salvos da extensão continuam os mesmos.
- O `--uninstall` apaga essa pasta; uma reinstalação depois disso gera um ID novo.

Assim, o projeto não fica preso a quem o publica: qualquer pessoa pode fazer um fork, gerar releases e instalar sem depender de chave nenhuma. O `check.py` falha se alguém adicionar uma `key` ao manifest do repositório.

> A chave privada só seria necessária para assinar um `.crx` (pacote fechado) com um ID fixo. Como a extensão é carregada sem compactação, isso não é usado.

## Se um dia for para uma loja

- Lojas de extensões (Chrome Web Store, Edge Add-ons) atribuem o próprio ID. Os usuários instalariam a extensão pela loja e o host com `EXT_ID=<id da loja> ./host/install.sh`.
- Firefox (AMO): precisa de um manifest próprio com `browser_specific_settings.gecko.id`, do registro em `~/.mozilla/native-messaging-hosts/` com `allowed_extensions`, e de `background.scripts` no lugar de `service_worker`.

## Atualizações para quem já usa

A extensão carregada sem compactação **não se atualiza sozinha**. Avise os usuários (por exemplo, nas notas do release) para:

1. Extrair o pacote novo e rodar `./host/install.sh`. Isso atualiza o host e a extensão e mantém o ID, o yt-dlp e o deno que já existem.
2. Clicar em ↻ no card da extensão em `chrome://extensions`. O instalador já atualizou os arquivos em `~/.local/share/yt-baixador/extension`.

As configurações e o histórico ficam guardados, porque o ID da instalação não muda.

O yt-dlp tem um ciclo de atualização próprio e muito mais frequente: o usuário atualiza pelo popup (⚙ → **Atualizar yt-dlp**), sem precisar de um release novo do YT Baixador.
