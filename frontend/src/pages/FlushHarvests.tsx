import { createSignal, onMount } from 'solid-js'
import { For, Show } from 'solid-js'
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
  const [endingId, setEndingId] = createSignal<number | null>(null)
  const [endForm, setEndForm] = createSignal({ endedAt: toLocalInput(), weightKg: '' })
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

  // 只能新建到 fruiting 且无进行中采收的室（服务端仍会以 409 兜底）
  function roomSelectable(r: Room) {
    return r.status === 'fruiting' && !r.openFlushHarvest
  }

  function roomLabel(r: Room) {
    const flags: string[] = []
    if (r.status !== 'fruiting') flags.push(r.status)
    if (r.openFlushHarvest) flags.push('有进行中采收')
    return `${r.roomCode} · ${r.species}${flags.length ? `（${flags.join(' · ')}）` : ''}`
  }

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

  function startEnd(r: FlushHarvest) {
    setEndingId(r.id)
    setEndForm({ endedAt: toLocalInput(), weightKg: '' })
    setError('')
  }

  async function submitEnd(e: Event) {
    e.preventDefault()
    const id = endingId()
    if (id == null) return
    setError('')
    try {
      await api(`/api/flush-harvests/${id}/end`, {
        method: 'POST',
        body: JSON.stringify({
          endedAt: new Date(endForm().endedAt).toISOString(),
          weightKg: Number(endForm().weightKg),
        }),
      })
      setEndingId(null)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '结束失败')
    }
  }

  async function remove(id: number) {
    if (!confirm('确认删除该进行中的采收记录？')) return
    try {
      await api(`/api/flush-harvests/${id}`, { method: 'DELETE' })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败')
    }
  }

  return (
    <div>
      <header class="page-header">
        <h1>采收记录</h1>
        <p class="muted">新建即进行中（未称重可暂存 0kg）；称重结束后禁止删除</p>
      </header>
      {error() && <div class="error">{error()}</div>}

      <form class="panel form-grid" onSubmit={onSubmit}>
        <label>
          出菇室
          <select
            value={form().roomId}
            onChange={(e) => setForm({ ...form(), roomId: e.currentTarget.value })}
            required
          >
            <option value="">选择出菇室</option>
            <For each={rooms()}>
              {(r) => (
                <option value={String(r.id)} disabled={!roomSelectable(r)}>
                  {roomLabel(r)}
                </option>
              )}
            </For>
          </select>
        </label>
        <label>
          采收时间
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
          重量 (kg)
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
          新增采收（进行中）
        </button>
      </form>

      <Show when={endingId() != null}>
        <form class="panel form-grid" onSubmit={submitEnd}>
          <label>
            称重结束时间
            <input
              type="datetime-local"
              value={endForm().endedAt}
              onInput={(e) => setEndForm({ ...endForm(), endedAt: e.currentTarget.value })}
              required
            />
          </label>
          <label>
            最终重量 (kg)
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={endForm().weightKg}
              onInput={(e) => setEndForm({ ...endForm(), weightKg: e.currentTarget.value })}
              required
            />
          </label>
          <button type="submit" class="btn primary">
            确认结束 #{endingId()}
          </button>
          <button type="button" class="btn ghost" onClick={() => setEndingId(null)}>
            取消
          </button>
        </form>
      </Show>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>室 ID</th>
              <th>采收时间</th>
              <th>结束时间</th>
              <th>状态</th>
              <th>潮次</th>
              <th>重量</th>
              <th>等级</th>
              <th>操作人</th>
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
                  <td>{r.endedAt ? new Date(r.endedAt).toLocaleString() : '—'}</td>
                  <td>
                    <span class={`badge ${r.open ? 'open' : 'ended'}`}>
                      {r.open ? '进行中' : '已结束'}
                    </span>
                  </td>
                  <td>{r.flushNo}</td>
                  <td>{r.weightKg}</td>
                  <td>
                    <span class={`badge grade-${r.grade.toLowerCase()}`}>{r.grade}</span>
                  </td>
                  <td>{r.operatorName}</td>
                  <td>
                    {r.open && (
                      <>
                        <button type="button" class="btn ghost" onClick={() => startEnd(r)}>
                          结束
                        </button>
                        <button type="button" class="btn ghost" onClick={() => remove(r.id)}>
                          删除
                        </button>
                      </>
                    )}
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
