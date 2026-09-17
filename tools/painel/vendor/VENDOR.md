# Vendor do painel — cópia local, pinada, sem CDN

> Padrão dsh: dependência de runtime entra como **cópia local versionada**, nunca como
> `<script src>` remoto. O painel tem de subir sem rede. `G13` verifica que a página
> servida não contém nenhuma URL externa.

## three@0.180.0

| | |
|---|---|
| **Versão** | `0.180.0` (r180) — pin do Hudson, 25/08/2026 |
| **Origem** | `npm pack three@0.180.0` → `https://registry.npmjs.org/three/-/three-0.180.0.tgz` |
| **Data da cópia** | 2026-08-25 |
| **Licença** | MIT (cópia em `three@0.180.0/LICENSE`) |
| **Arquivos** | `three.module.min.js` (331 KB) · `three.core.min.js` (372 KB) |

**SHA-256** (byte a byte iguais aos do pacote npm):

```
e2b5ee6bccd38fd6d8a2428546b83c5f2426d84b152ef82be8055556e3b40eb6  three.module.min.js
61ba0df005b05991361d040d8ff670e1aadfd0ce7aeebd1fdb0725957a8957de  three.core.min.js
```

### O SHA tem de bater em qualquer maquina

`.gitattributes` marca `tools/painel/vendor/** -text`: sem isso, `core.autocrlf=true`
entregaria estes arquivos com CRLF num clone Windows e o SHA acima deixaria de conferir
no working tree — a auditoria que ele existe para permitir.

### Por que DOIS arquivos

Em r180 o build é partido: `three.module.js` só re-exporta de `three.core.js`. Vendorizar
um sem o outro deixa a página com um import quebrado. São sempre os dois.

### Por que o build MINIFICADO

1959 KB legíveis contra **703 KB** minificados, para um blob que ninguém vai ler linha a
linha. A auditabilidade vem do **SHA-256** acima — qualquer um confere que é idêntico ao
artefato do npm — não de o arquivo ser legível.

### Por que NÃO vendorizamos o OrbitControls

`examples/jsm/controls/OrbitControls.js` (38 KB) importa do **bare specifier `'three'`**:

```js
import { Controls, MOUSE, Quaternion, Spherical, TOUCH, Vector2, Vector3, Plane, Ray, MathUtils } from 'three';
```

Usá-lo exigiria um **import map** na página, e o arquivo vem de `examples/` — a pasta que
o upstream reorganiza entre versões (foi o atrito que o Hudson previu ao pinar r180).
Seriam duas dependências de forma — o arquivo e o import map — para ganhar recursos que
a fronteira da célula não pede.

**Decisão (critério do Hudson: o mais simples de testar e manter offline, não o mais
completo):** órbita própria em ~40 linhas — drag = rotate, scroll = zoom, drag direito =
pan. O `three.module.min.js` é importado por caminho, sem import map.

## Como atualizar

Subir de versão é **célula própria**, como o `cordis` (política da C2): trocar os dois
arquivos, recalcular os SHA, atualizar esta tabela, e rodar a série G inteira como gate
de regressão.
