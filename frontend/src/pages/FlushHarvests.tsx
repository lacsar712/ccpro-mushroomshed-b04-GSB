import { createSignal, onMount } from 'solid-js'
import { For } from 'solid-js'
import { api } from '../api/client'
import type { FlushHarvest, HarvestGrade, Room } from '../types'

const grades: HarvestGrade[] = ['A', 'B', 'C']

function toLocalInput(iso?: string) {
  const d = iso ? new Date(iso) : new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const empty = {
  roomId: '',
  harvestedAt: toLocalInput(),
  flushNo: '1',
  weightKg: '0',
  grade: 'A' as HarvestGrade,
  operatorName: '',
}

export default function FlushHarvests() {
  const [rows, setRows] = createSignal<FlushHarvest[]>([])
  const [rooms, setRooms] = createSignal<Room[]>([])
  const [form, setForm] = createSignal({ ...empty })
  const [error, setError] = createSignal('')

  async function load() {
    const [harvests, roomList] = await Promise.all([
      api<FlushHarvest[]>('/api/flush-harvests'),
      api<Room[]>('/api/rooms'),
    ])
    setRows(harvests)
    setRooms(roomList)
  }

  onMount(() => {
    load().catch((e) => setError(e.message))
  })

  async function onSubmit(e: Event) {
    e.preventDefault()
    setError('')
    try {
      await api('/api/flush-harvests', {
        method: 'POST',
        body: JSON.stringify({
          roomId: Number(form().roomId),
          harvestedAt: new Date(form().harvestedAt).toISOString(),
          flushNo: Number(form().flushNo),
          weightKg: Number(form().weightKg),
          grade: form().grade,
          operatorName: form().operatorName,
        }),
      })
      setForm({ ...empty, harvestedAt: toLocalInput() })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    }
  }

  // 称重结束：open 状态由服务端返回，前端不自行判断/计数。
  async function finish(r: FlushHarvest) {
    const input = prompt(`为 #${r.id} 潮次输入实际称重重量 (kg，须 > 0)`, r.weightKg > 0 ? String(r.weightKg) : '')
    if (input === null) return
    const weightKg = Number(input)
    if (!Number.isFinite(weightKg) || weightKg <= 0) {
      setError('weightKg 须大于 0')
      return
    }
    setError('')
    try {
      await api(`/api/flush-harvests/${r.id}/end`, {
        method: 'POST',
        body: JSON.stringify({ weightKg, endedAt: new Date().toISOString() }),
      })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '结束失败')
    }
  }

  async function remove(r: FlushHarvest) {
    if (!r.open) {
      setError('已称重结束的记录禁止删除')
      return
    }
    if (!confirm(`确认删除进行中的采收记录 #${r.id}？`)) return
    try {
      await api(`/api/flush-harvests/${r.id}`, { method: 'DELETE' })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败')
    }
  }

  return (
    <div>
      <header class="page-header">
        <h1>采收记录</h1>
        <p class="muted">
          开潮即「进行中」（weightKg 可填 0），称重后结束并填入实际重量；同室同时仅一条进行中
        </p>
      </header>
      {error() && <div class="error">{error()}</div>}

      <form class="panel form-grid" onSubmit={onSubmit}>
        <label>
          出菇室（仅 fruiting 可开潮）
          <select
            value={form().roomId}
            onChange={(e) => setForm({ ...form(), roomId: e.currentTarget.value })}
            required
          >
            <option value="">选择出菇室</option>
            <For each={rooms()}>
              {(r) => (
                <option value={String(r.id)} disabled={r.status !== 'fruiting' || r.openFlushHarvest}>
                  {r.roomCode} · {r.species}
                  {r.status !== 'fruiting' ? '（非 fruiting）' : r.openFlushHarvest ? '（进行中潮次未结束）' : ''}
                </option>
              )}
            </For>
          </select>
        </label>
        <label>
          开潮时间
          <input
            type="datetime-local"
            value={form().harvestedAt}
            onInput={(e) => setForm({ ...form(), harvestedAt: e.currentTarget.value })}
            required
          />
        </label>
        <label>
          潮次
          <input
            type="number"
            min="1"
            value={form().flushNo}
            onInput={(e) => setForm({ ...form(), flushNo: e.currentTarget.value })}
            required
          />
        </label>
        <label>
          初始重量 (kg，进行中可填 0)
          <input
            type="number"
            step="0.01"
            min="0"
            value={form().weightKg}
            onInput={(e) => setForm({ ...form(), weightKg: e.currentTarget.value })}
            required
          />
        </label>
        <label>
          等级
          <select
            value={form().grade}
            onChange={(e) =>
              setForm({ ...form(), grade: e.currentTarget.value as HarvestGrade })
            }
          >
            <For each={grades}>{(g) => <option value={g}>{g}</option>}</For>
          </select>
        </label>
        <label>
          操作人
          <input
            value={form().operatorName}
            onInput={(e) => setForm({ ...form(), operatorName: e.currentTarget.value })}
            required
          />
        </label>
        <button type="submit" class="btn primary">
          开潮（进行中）
        </button>
      </form>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>室 ID</th>
              <th>开潮时间</th>
              <th>潮次</th>
              <th>重量</th>
              <th>等级</th>
              <th>操作人</th>
              <th>状态</th>
              <th>结束时间</th>
              <th />
            </tr>
          </thead>
          <tbody>
            <For each={rows()}>
              {(r) => (
                <tr>
                  <td>{r.id}</td>
                  <td>{r.roomId}</td>
                  <td>{new Date(r.harvestedAt).toLocaleString()}</td>
                  <td>{r.flushNo}</td>
                  <td>{r.weightKg}</td>
                  <td>
                    <span class={`badge grade-${r.grade.toLowerCase()}`}>{r.grade}</span>
                  </td>
                  <td>{r.operatorName}</td>
                  <td>
                    {r.open ? (
                      <span class="badge fruiting">进行中</span>
                    ) : (
                      <span class="badge idle">已称重结束</span>
                    )}
                  </td>
                  <td>{r.endedAt ? new Date(r.endedAt).toLocaleString() : '—'}</td>
                  <td>
                    {r.open && (
                      <button type="button" class="btn primary" onClick={() => finish(r)}>
                        称重结束
                      </button>
                    )}
                    <button
                      type="button"
                      class="btn ghost"
                      disabled={!r.open}
                      title={r.open ? '' : '已结束记录禁止删除'}
                      onClick={() => remove(r)}
                    >
                      删除
                    </button>
                  </td>
                </tr>
              )}
            </For>
          </tbody>
        </table>
      </div>
    </div>
  )
}
