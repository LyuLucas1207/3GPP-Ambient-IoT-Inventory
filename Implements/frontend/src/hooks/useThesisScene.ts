import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  createSection,
  fetchCatalog,
  fetchScenarioDefaults,
  fetchSection,
  fetchSections,
  patchPlacement,
  patchSection,
  postPlacement,
  postPlacementBatch,
  patchPlacementBatch,
  convertPlacements as postConvertPlacements,
  deleteSection,
  removePlacement,
  removePlacementBatch,
} from '@/api/thesisSimulator'
import { clearDraft, loadDraft, saveDraft } from '@/lib/thesisDraft'
import {
  cloneParams,
  DEFAULT_HEIGHT_M,
  DEFAULT_WIDTH_M,
  findCatalog,
  inside,
  MAX_BULK,
  intervalGrid,
  randomPoints,
} from '@/lib/thesisGeometry'
import type {
  CatalogEntry,
  DeviceMix,
  Kind,
  Params,
  Placement,
  PlacementId,
  PlacementInput,
  ScenarioDefaults,
  Scene,
  SectionDetail,
  SectionSummary,
} from '@/types/thesis'

function explain(err: unknown, t: (key: string) => string) {
  const raw = err instanceof Error ? err.message : 'request_failed'
  if (raw === 'Failed to fetch') return t('thesis.errors.network')
  const key = `thesis.errors.${raw}`
  const translated = t(key)
  return translated === key ? raw : translated
}

function nextId() {
  return `tmp-${crypto.randomUUID()}`
}

function fromServer(detail: SectionDetail): Scene {
  return {
    id: detail.id,
    name: detail.name,
    width_m: detail.width_m,
    height_m: detail.height_m,
    placements: detail.placements,
    dirty: false,
    saved: true,
    status: detail.status,
    locked: detail.status === 'initialized',
    markerScale: detail.marker_scale ?? 0.7,
    deviceMarkerScale: detail.device_marker_scale ?? 0.3,
    nonce: detail.id,
  }
}

export function useThesisScene() {
  const { t } = useTranslation()
  const [catalog, setCatalog] = useState<CatalogEntry[]>([])
  const [pristineCatalog, setPristineCatalog] = useState<CatalogEntry[]>([])
  const [scenarioDefaults, setScenarioDefaults] = useState<ScenarioDefaults | null>(null)
  const [sections, setSections] = useState<SectionSummary[]>([])
  const [scene, setScene] = useState<Scene | null>(() => loadDraft())
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sceneRef = useRef(scene)
  useEffect(() => {
    sceneRef.current = scene
  }, [scene])

  const fail = useCallback(
    (err: unknown) => {
      setError(explain(err, t))
    },
    [t],
  )

  const refreshSections = useCallback(async () => {
    setSections(await fetchSections())
  }, [])

  useEffect(() => {
    let cancel = false
    void (async () => {
      try {
        const [nextCatalog, nextSections, nextScenario] = await Promise.all([
          fetchCatalog(),
          fetchSections(),
          fetchScenarioDefaults(),
        ])
        if (cancel) return
        setCatalog(nextCatalog)
        setPristineCatalog(nextCatalog.map((entry) => ({ ...entry, defaults: { ...entry.defaults } })))
        setSections(nextSections)
        setScenarioDefaults(nextScenario)
        // No unsaved draft and nothing open → open the newest section (list is updated_at desc).
        if (!sceneRef.current && nextSections.length > 0) {
          const detail = await fetchSection(nextSections[0].id)
          if (!cancel) {
            setScene(fromServer(detail))
            clearDraft()
          }
        }
      } catch (err) {
        if (!cancel) fail(err)
      }
    })()
    return () => {
      cancel = true
    }
  }, [fail])

  useEffect(() => {
    if (scene && !scene.saved) saveDraft(scene)
    else if (scene?.saved) clearDraft()
  }, [scene])

  const confirmDiscard = useCallback(() => {
    const current = sceneRef.current
    if (!current || current.saved || !current.dirty) return true
    return window.confirm(t('thesis.discardConfirm'))
  }, [t])

  const createSavedSection = useCallback(
    async (name: string) => {
      const trimmed = name.trim()
      if (!trimmed) {
        setError(t('thesis.errors.empty_name'))
        return false
      }
      if (!confirmDiscard()) return false
      setBusy(true)
      setError(null)
      try {
        const detail = await createSection({
          name: trimmed,
          width_m: scenarioDefaults?.width_m ?? DEFAULT_WIDTH_M,
          height_m: scenarioDefaults?.height_m ?? DEFAULT_HEIGHT_M,
          placements: [],
        })
        setScene(fromServer(detail))
        clearDraft()
        await refreshSections()
        return true
      } catch (err) {
        fail(err)
        return false
      } finally {
        setBusy(false)
      }
    },
    [confirmDiscard, fail, refreshSections, scenarioDefaults, t],
  )

  const openSection = useCallback(
    async (id: number) => {
      if (!confirmDiscard()) return
      setBusy(true)
      setError(null)
      try {
        const detail = await fetchSection(id)
        setScene(fromServer(detail))
        clearDraft()
      } catch (err) {
        fail(err)
      } finally {
        setBusy(false)
      }
    },
    [confirmDiscard, fail],
  )

  const save = useCallback(async () => {
    const current = sceneRef.current
    if (!current || current.saved) return
    const name = current.name.trim()
    if (!name) {
      setError(t('thesis.errors.empty_name'))
      return
    }
    setBusy(true)
    setError(null)
    try {
      const detail = await createSection({
        name,
        width_m: current.width_m,
        height_m: current.height_m,
        placements: current.placements.map(({ kind, subtype, x_m, y_m, params }) => ({
          kind,
          subtype,
          x_m,
          y_m,
          params,
        })),
      })
      setScene(fromServer(detail))
      clearDraft()
      await refreshSections()
    } catch (err) {
      fail(err)
    } finally {
      setBusy(false)
    }
  }, [fail, refreshSections, t])

  const markInitialized = useCallback(async () => {
    const current = sceneRef.current
    if (!current?.saved || current.id == null || current.status === 'initialized') return
    setBusy(true)
    setError(null)
    try {
      const detail = await patchSection(current.id, { status: 'initialized' })
      setScene(fromServer(detail))
      await refreshSections()
    } catch (err) {
      fail(err)
    } finally {
      setBusy(false)
    }
  }, [fail, refreshSections])

  const removeSection = useCallback(
    async (id: number) => {
      setBusy(true)
      setError(null)
      try {
        await deleteSection(id)
        const wasOpen = sceneRef.current?.id === id
        if (wasOpen) setScene(null)
        const nextSections = await fetchSections()
        setSections(nextSections)
        // After deleting the open section, fall through to the newest remaining one.
        if (wasOpen && nextSections.length > 0) {
          const detail = await fetchSection(nextSections[0].id)
          setScene(fromServer(detail))
          clearDraft()
        }
      } catch (err) {
        fail(err)
      } finally {
        setBusy(false)
      }
    },
    [fail],
  )

  const applySize = useCallback(
    async (width: number, height: number) => {
      const current = sceneRef.current
      if (!current) return false
      if (current.locked) {
        setError(t('thesis.errors.size_locked'))
        return false
      }
      if (!(width > 0) || !(height > 0) || width > 10_000 || height > 10_000) {
        setError(t('thesis.errors.bad_size'))
        return false
      }
      if (current.placements.some((item) => !inside(item.x_m, item.y_m, width, height))) {
        setError(t('thesis.errors.outside_bounds'))
        return false
      }
      if (!current.saved) {
        setScene({ ...current, width_m: width, height_m: height, dirty: true })
        setError(null)
        return true
      }
      if (current.id == null) return false
      setBusy(true)
      setError(null)
      try {
        const detail = await patchSection(current.id, { width_m: width, height_m: height })
        setScene((prev) => (prev ? { ...prev, width_m: detail.width_m, height_m: detail.height_m } : prev))
        await refreshSections()
        return true
      } catch (err) {
        fail(err)
        return false
      } finally {
        setBusy(false)
      }
    },
    [fail, refreshSections, t],
  )

  const setMarkerScale = useCallback(
    async (scale: number) => {
      const value = Math.min(5, Math.max(0, Math.round(scale * 10) / 10))
      const current = sceneRef.current
      if (!current) return
      setScene({ ...current, markerScale: value })
      if (!current.saved || current.id == null) return
      try {
        await patchSection(current.id, { marker_scale: value })
      } catch (err) {
        fail(err)
      }
    },
    [fail],
  )

  const setDeviceMarkerScale = useCallback(
    async (scale: number) => {
      const value = Math.min(5, Math.max(0, Math.round(scale * 10) / 10))
      const current = sceneRef.current
      if (!current) return
      setScene({ ...current, deviceMarkerScale: value })
      if (!current.saved || current.id == null) return
      try {
        await patchSection(current.id, { device_marker_scale: value })
      } catch (err) {
        fail(err)
      }
    },
    [fail],
  )

  const addOne = useCallback(
    async (input: PlacementInput) => {
      const current = sceneRef.current
      if (!current) return
      if (!inside(input.x_m, input.y_m, current.width_m, current.height_m)) {
        setError(t('thesis.errors.outside_bounds'))
        return
      }
      if (!current.saved) {
        const placement: Placement = { ...input, id: nextId(), params: cloneParams(input.params) }
        setScene({ ...current, dirty: true, placements: [...current.placements, placement] })
        setError(null)
        return
      }
      if (current.id == null) return
      setBusy(true)
      setError(null)
      try {
        const created = await postPlacement(current.id, input)
        setScene((prev) => (prev ? { ...prev, placements: [...prev.placements, created] } : prev))
        await refreshSections()
      } catch (err) {
        fail(err)
      } finally {
        setBusy(false)
      }
    },
    [fail, refreshSections, t],
  )

  const addMany = useCallback(
    async (inputs: PlacementInput[]) => {
      const current = sceneRef.current
      if (!current || current.status === 'initialized') {
        setError(t('thesis.errors.bulk_locked'))
        return
      }
      if (!current.saved || current.id == null) {
        const placements = inputs.map((input) => ({ ...input, id: nextId(), params: cloneParams(input.params) }))
        setScene({ ...current, dirty: true, placements: [...current.placements, ...placements] })
        setError(null)
        return
      }
      const sectionId = current.id
      setBusy(true)
      setError(null)
      try {
        const created: Placement[] = []
        for (let i = 0; i < inputs.length; i += MAX_BULK) {
          const chunk = inputs.slice(i, i + MAX_BULK)
          const rows = await postPlacementBatch(sectionId, chunk)
          created.push(...rows)
        }
        setScene((prev) => (prev ? { ...prev, placements: [...prev.placements, ...created] } : prev))
        await refreshSections()
      } catch (err) {
        fail(err)
      } finally {
        setBusy(false)
      }
    },
    [fail, refreshSections, t],
  )

  const updatePlacement = useCallback(
    async (id: PlacementId, input: PlacementInput) => {
      const current = sceneRef.current
      if (!current) return
      if (!inside(input.x_m, input.y_m, current.width_m, current.height_m)) {
        setError(t('thesis.errors.outside_bounds'))
        return
      }
      if (!current.saved) {
        setScene({
          ...current,
          dirty: true,
          placements: current.placements.map((item) =>
            item.id === id ? { ...item, ...input, id: item.id, params: cloneParams(input.params) } : item,
          ),
        })
        setError(null)
        return
      }
      if (current.id == null || typeof id !== 'number') return
      setBusy(true)
      setError(null)
      try {
        const updated = await patchPlacement(current.id, id, input)
        setScene((prev) =>
          prev ? { ...prev, placements: prev.placements.map((item) => (item.id === id ? updated : item)) } : prev,
        )
      } catch (err) {
        fail(err)
      } finally {
        setBusy(false)
      }
    },
    [fail, t],
  )

  const deletePlacement = useCallback(
    async (id: PlacementId) => {
      const current = sceneRef.current
      if (!current) return
      if (!current.saved) {
        setScene({ ...current, dirty: true, placements: current.placements.filter((item) => item.id !== id) })
        return
      }
      if (current.id == null || typeof id !== 'number') return
      setBusy(true)
      setError(null)
      try {
        await removePlacement(current.id, id)
        setScene((prev) => (prev ? { ...prev, placements: prev.placements.filter((item) => item.id !== id) } : prev))
        await refreshSections()
      } catch (err) {
        fail(err)
      } finally {
        setBusy(false)
      }
    },
    [fail, refreshSections],
  )

  const clearPlacements = useCallback(
    async (which: 'device' | 'infra') => {
      const current = sceneRef.current
      if (!current || current.status === 'initialized') {
        setError(t('thesis.errors.bulk_locked'))
        return
      }
      const keep = (item: Placement) => (which === 'device' ? item.kind !== 'device' : item.kind === 'device')
      if (!current.saved || current.id == null) {
        setScene({ ...current, dirty: true, placements: current.placements.filter(keep) })
        return
      }
      setBusy(true)
      setError(null)
      try {
        const ids = current.placements
          .filter((item): item is Placement & { id: number } => !keep(item) && typeof item.id === 'number')
          .map((item) => item.id)
        if (ids.length > 0) await removePlacementBatch(current.id, ids)
        setScene((prev) => (prev ? { ...prev, placements: prev.placements.filter(keep) } : prev))
        await refreshSections()
      } catch (err) {
        fail(err)
      } finally {
        setBusy(false)
      }
    },
    [fail, refreshSections, t],
  )

  const addRandomDevices = useCallback(
    (count: number, mix: DeviceMix) => {
      const current = sceneRef.current
      if (!Number.isInteger(count) || count < 1) {
        setError(t('thesis.errors.bad_count'))
        return
      }
      const points = randomPoints(count, current?.width_m ?? 0, current?.height_m ?? 0)
      const subtypes = ['1', '2a', '2b'] as const
      const inputs: PlacementInput[] = []
      for (const point of points) {
        const subtype = mix === 'mixed' ? subtypes[Math.floor(Math.random() * subtypes.length)] : mix
        const entry = findCatalog(catalog, 'device', subtype)
        if (!entry) {
          setError(t('thesis.errors.network'))
          return
        }
        inputs.push({ kind: 'device', subtype, x_m: point.x_m, y_m: point.y_m, params: cloneParams(entry.defaults) })
      }
      addMany(inputs)
    },
    [addMany, catalog, t],
  )

  const addRandomStations = useCallback(
    (count: number) => {
      const current = sceneRef.current
      if (!Number.isInteger(count) || count < 1) {
        setError(t('thesis.errors.bad_count'))
        return
      }
      const entry = findCatalog(catalog, 'station', null)
      if (!entry || !current) {
        setError(t('thesis.errors.network'))
        return
      }
      addMany(
        randomPoints(count, current.width_m, current.height_m).map((point) => ({
          kind: 'station' as const,
          subtype: null,
          x_m: point.x_m,
          y_m: point.y_m,
          params: cloneParams(entry.defaults),
        })),
      )
    },
    [addMany, catalog, t],
  )

  const applyStandardLayout = useCallback(() => {
    const current = sceneRef.current
    const entry = findCatalog(catalog, 'station', null)
    if (!entry || !current || !scenarioDefaults) {
      setError(t('thesis.errors.network'))
      return
    }
    void addMany(
      scenarioDefaults.bs_positions.map(([x, y]) => ({
        kind: 'station' as const,
        subtype: null,
        x_m: x,
        y_m: y,
        params: cloneParams(entry.defaults),
      })),
    )
  }, [addMany, catalog, scenarioDefaults, t])

  const addStationGrid = useCallback(
    (spacingX: number, spacingY: number) => {
      const current = sceneRef.current
      const entry = findCatalog(catalog, 'station', null)
      if (!entry || !current) {
        setError(t('thesis.errors.network'))
        return
      }
      if (!(spacingX > 0) || !(spacingY > 0)) {
        setError(t('thesis.errors.grid_empty'))
        return
      }
      const grid = intervalGrid(current.width_m, current.height_m, spacingX, spacingY)
      if (grid.capped) {
        setError(t('thesis.errors.too_many'))
        return
      }
      if (grid.points.length === 0) {
        setError(t('thesis.errors.grid_empty'))
        return
      }
      void addMany(
        grid.points.map((point) => ({
          kind: 'station' as const,
          subtype: null,
          x_m: point.x_m,
          y_m: point.y_m,
          params: cloneParams(entry.defaults),
        })),
      )
    },
    [addMany, catalog, t],
  )

  const setCatalogValue = useCallback((kind: Kind, subtype: string | null, key: string, value: Params[string]) => {
    setCatalog((prev) =>
      prev.map((entry) =>
        entry.kind === kind && entry.subtype === subtype
          ? { ...entry, defaults: { ...entry.defaults, [key]: value } }
          : entry,
      ),
    )
  }, [])

  const resetCatalog = useCallback(
    (kind: Kind, subtype: string | null) => {
      const pristine = pristineCatalog.find((entry) => entry.kind === kind && entry.subtype === subtype)
      if (!pristine) return
      setCatalog((prev) =>
        prev.map((entry) =>
          entry.kind === kind && entry.subtype === subtype ? { ...entry, defaults: { ...pristine.defaults } } : entry,
        ),
      )
    },
    [pristineCatalog],
  )

  const applyKindParams = useCallback(
    async (kind: Kind, subtype: string | null, params: Params) => {
      const current = sceneRef.current
      if (!current) return
      if (current.locked) {
        setError(t('thesis.errors.scene_locked'))
        return
      }
      const matches = (item: Placement) => item.kind === kind && (kind !== 'device' || item.subtype === subtype)
      if (!current.saved || current.id == null) {
        setScene({
          ...current,
          dirty: true,
          placements: current.placements.map((item) =>
            matches(item) ? { ...item, params: { ...item.params, ...cloneParams(params) } } : item,
          ),
        })
        return
      }
      setBusy(true)
      setError(null)
      try {
        const updated = await patchPlacementBatch(current.id, { kind, subtype, params })
        const byId = new Map(updated.map((item) => [item.id, item]))
        setScene((prev) =>
          prev
            ? {
                ...prev,
                placements: prev.placements.map((item) => byId.get(item.id) ?? item),
              }
            : prev,
        )
      } catch (err) {
        fail(err)
      } finally {
        setBusy(false)
      }
    },
    [fail, t],
  )

  const convertPlacements = useCallback(
    async (ids: Array<number | string>, kind: 'station' | 'radar') => {
      const current = sceneRef.current
      if (!current || ids.length === 0) return
      if (current.locked) {
        setError(t('thesis.errors.scene_locked'))
        return
      }
      const idSet = new Set(ids.map(String))
      const nextOf = (item: Placement): Placement => {
        if (!idSet.has(String(item.id)) || item.kind === 'device' || item.kind === kind) return item
        return { ...item, kind, subtype: null, params: { ...item.params } }
      }
      if (!current.saved || current.id == null) {
        setScene({ ...current, dirty: true, placements: current.placements.map(nextOf) })
        return
      }
      const numeric = ids.filter((id): id is number => typeof id === 'number')
      if (numeric.length === 0) return
      setBusy(true)
      setError(null)
      try {
        const updated = await postConvertPlacements(current.id, { ids: numeric, kind })
        const byId = new Map(updated.map((item) => [item.id, item]))
        setScene((prev) =>
          prev ? { ...prev, placements: prev.placements.map((item) => byId.get(item.id as number) ?? item) } : prev,
        )
      } catch (err) {
        fail(err)
      } finally {
        setBusy(false)
      }
    },
    [fail, t],
  )

  return {
    catalog,
    pristineCatalog,
    scenarioDefaults,
    sections,
    scene,
    busy,
    error,
    clearError: () => setError(null),
    createSavedSection,
    openSection,
    save,
    markInitialized,
    removeSection,
    applySize,
    setMarkerScale,
    setDeviceMarkerScale,
    addOne,
    updatePlacement,
    deletePlacement,
    clearPlacements,
    addRandomDevices,
    addRandomStations,
    addStationGrid,
    applyStandardLayout,
    setCatalogValue,
    resetCatalog,
    applyKindParams,
    convertPlacements,
  }
}
