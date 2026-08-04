# Asset Hierarchy Model

> **Milestone 6** · Parent/child links in `cim_assets`

---

## Principles

1. Hierarchy is **optional** and only created when metadata provides both ends.
2. Do **not** invent parents from missing fields.
3. Unique key remains `(identifier, type)`.
4. Infra and research chains are independent.

---

## Supported chains

### Infrastructure

```
site → data_centre → cluster → rack → node → server
                              ↘ node → gpu / cpu / virtual_machine / container / service
```

### Research / experiment

```
workflow → workflow_run
dataset (standalone)
experiment (standalone)
```

---

## Examples

| Metadata | Result |
|----------|--------|
| `cluster=cluster-A`, `node=hpc-node-07` | node under cluster |
| `+ gpu_id=gpu-0` | gpu under node; node under cluster |
| `site=RI-site-1` + cluster | cluster under site |
| `workflow_id=wf-204`, `workflow_run_id=run-001` | run under workflow |
| only `node=…` | node with `parent_id=NULL` |

---

## API

```python
svc = AssetRegistryService(session)
leaf = svc.resolve_from_metadata(meta, build_hierarchy=True)
chain = svc.get_hierarchy(leaf.asset_id)  # root → leaf
```
