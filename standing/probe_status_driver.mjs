// SONDA DESCARTAVEL — nao entra em resultado do paper.
// standing-cli.js exposes only partitionByStanding; the status cell (status.js)
// has NO CLI. This driver reproduces recommend.ts lines 43-61 verbatim:
// partitionByStanding -> statusPortrait(warranting) -> electedStrategy(warranting).
import { pathToFileURL } from 'node:url';

const dist = process.env.MDAA_PLUGIN_DIST;
if (!dist) throw new Error('MDAA_PLUGIN_DIST not set');
const mod = (f) => import(pathToFileURL(`${dist}/${f}`).href);
const { partitionByStanding } = await mod('standing.js');
const { statusPortrait, electedStrategy } = await mod('status.js');

const chunks = [];
for await (const c of process.stdin) chunks.push(c);
const req = JSON.parse(Buffer.concat(chunks).toString('utf8'));
// contract.ts: strategy is readonly string[]; the bench payload writes a scalar.
const obs = req.observations.map((o) => ({
  ...o, strategy: Array.isArray(o.strategy) ? o.strategy : [o.strategy],
}));
const part = partitionByStanding(obs, req.nowSeq, req.currentConditions, req.vocabularyEvents, req.policy);
const portrait = statusPortrait(part.warranting, req.currentConditions);
const elected = electedStrategy(part.warranting, req.currentConditions, []);

const seqs = (a) => (a && a.length ? [a[0].seq, a[a.length - 1].seq] : null);
process.stdout.write(`${JSON.stringify({
  nWarranting: part.warranting.length,
  nAppearing: part.appearing.length,
  elected: elected ?? null,
  byProposition: portrait.byProposition.map((p) => ({
    strategy: p.strategy,
    conditions: p.conditions,
    kind: p.status.kind,
    reason: p.status.reason ?? null,
    nSupporting: p.status.supporting ? p.status.supporting.length : 0,
    nContradicting: p.status.contradicting ? p.status.contradicting.length : 0,
    supportingSeqRange: seqs(p.status.supporting),
    contradictingSeqRange: seqs(p.status.contradicting),
  })),
  nConflicts: portrait.conflicts.length,
})}\n`);
