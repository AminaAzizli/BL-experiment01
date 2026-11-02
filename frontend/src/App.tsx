import { startTransition, useCallback, useEffect, useEffectEvent, useMemo, useState } from 'react'
import { enqueueResearchEvent, flushQueuedResearchEvents } from './lib/eventQueue'
import './App.css'

type Product = {
  id: string
  title: string
  author: string
  genre: string
  price: number
  rating: number
  reviews: number
  in_stock: boolean
  description: string
  is_reviewed: boolean
}

type VersionData = {
  name: string
  products: Product[]
  feature_flags: Record<string, boolean>
}

type Task = 'T1' | 'T5'

type CartEntry = {
  product: Product
  quantity: number
}

type FormValues = {
  full_name: string
  phone: string
  address: string
  notes: string
}

type ExperimentResult = {
  session_id: string
  run_id: string | null
  actor_type: 'human' | 'ai'
  persona: string
  model_name: string | null
  version: 'A' | 'B'
  task_id: string | null
  status: string
  duration_seconds: number | null
  event_count: number
  actions: number
  retries: number
  errors: number
  failed_attempts: number
  success: boolean | null
}

const TASKS: Task[] = ['T1', 'T5']
const TASK_INSTRUCTIONS: Record<Task, string> = {
  T1: 'Find the book Signal in the Dust and add it to your shopping cart.',
  T5: 'Change the quantity of the book in your cart from one to two and verify that the cart total has been updated.',
}
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const startupParams = new URLSearchParams(window.location.search)
const requestedTask = startupParams.get('task')
const initialTask: Task = requestedTask === 'T5' ? 'T5' : 'T1'
const initialVersion = startupParams.get('version') === 'B' ? 'B' : 'A'
const initialSessionId = startupParams.get('session_id') ?? ''
const isAgentSession = startupParams.get('actor') === 'ai'

const currency = (value: number) => `$${value.toFixed(2)}`

function resultOutcomeLabel(result: ExperimentResult): string {
  if (result.success === null) return result.status
  return result.success ? 'Success' : 'Not successful'
}

function App() {
  const [health, setHealth] = useState<{ status: string; app_name: string } | null>(null)
  const [versions, setVersions] = useState<{
    version_a?: VersionData
    version_b?: VersionData
    parity_check?: {
      status?: 'passed' | 'failed'
      matched_product_count: number
      same_actions: boolean
      same_prices: boolean
      same_descriptions: boolean
      message: string
    }
  } | null>(null)
  const [selectedVersion, setSelectedVersion] = useState<'A' | 'B'>(initialVersion)
  const [task, setTask] = useState<Task>(initialTask)
  const [search, setSearch] = useState('')
  const [genreFilter, setGenreFilter] = useState('All')
  const [maxPrice, setMaxPrice] = useState(25)
  const [cart, setCart] = useState<Record<string, CartEntry>>({})
  const [pendingQty, setPendingQty] = useState<Record<string, number>>({})
  const [form, setForm] = useState<FormValues>({
    full_name: '',
    phone: '',
    address: '',
    notes: '',
  })
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof FormValues, string>>>({})
  const [toast, setToast] = useState('')
  const [sessionId, setSessionId] = useState(initialSessionId)
  const [consentGiven, setConsentGiven] = useState(false)
  const [runStarting, setRunStarting] = useState(false)
  const [taskVerified, setTaskVerified] = useState(false)
  const [results, setResults] = useState<ExperimentResult[]>([])
  function loadTaskState(nextTask: Task, data = versions) {
    const productList = selectedVersion === 'A' ? (data?.version_a?.products ?? []) : (data?.version_b?.products ?? [])
    const seedCart: Record<string, CartEntry> = {}
    if (nextTask === 'T5') {
      const product = productList[0]
      if (product) seedCart[product.id] = { product, quantity: 1 }
    }
    setTask(nextTask)
    setCart(seedCart)
    setPendingQty({})
    setSearch('')
    setGenreFilter('All')
    setMaxPrice(25)
    setForm({ full_name: 'Fictional customer', phone: '555-0100', address: '123 Demo Street', notes: '' })
    setFormErrors({})
    setTaskVerified(false)
  }

  const loadResults = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/results`)
      if (response.ok) {
        const data = await response.json()
        startTransition(() => setResults(data))
      }
    } catch (error) {
      console.error('Failed to load experiment results', error)
    }
  }, [])

  const applyInitialData = useEffectEvent((healthData: { status: string; app_name: string }, data: typeof versions) => {
    setHealth(healthData)
    setVersions(data)
    loadTaskState(initialTask, data)
  })

  const loadResultsOnMount = useEffectEvent(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/results`)
      if (response.ok) {
        const data = await response.json()
        startTransition(() => setResults(data))
      }
    } catch (error) {
      console.error('Failed to load experiment results', error)
    }
  })

  useEffect(() => {
    const loadData = async () => {
      try {
        const healthResponse = await fetch(`${API_BASE_URL}/api/health`)
        const bookstoreResponse = await fetch(`${API_BASE_URL}/api/bookstore/versions`)
        if (healthResponse.ok && bookstoreResponse.ok) {
          const healthData = await healthResponse.json()
          const data = await bookstoreResponse.json()
          applyInitialData(healthData, data)
        }
      } catch (error) {
        console.error('Failed to load BehaviourLens data', error)
      }
    }

    void loadData()
  }, [])

  useEffect(() => {
    if (!sessionId) return
    const handleOnline = () => void flushQueuedResearchEvents(sessionId)
    window.addEventListener('online', handleOnline)
    const retryTimer = window.setInterval(handleOnline, 5000)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.clearInterval(retryTimer)
    }
  }, [sessionId])

  useEffect(() => {
    void loadResultsOnMount()
  }, [])

  const activeVersion = useMemo(() => {
    if (!versions) {
      return { name: 'Version A', products: [], feature_flags: {} } as VersionData
    }
    return selectedVersion === 'A' ? versions.version_a ?? versions.version_b ?? { name: 'Version A', products: [], feature_flags: {} } : versions.version_b ?? versions.version_a ?? { name: 'Version B', products: [], feature_flags: {} }
  }, [selectedVersion, versions])

  const activeProducts = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase()
    return activeVersion.products.filter((product) => {
      const matchesSearch =
        !normalizedSearch ||
        product.title.toLowerCase().includes(normalizedSearch) ||
        product.author.toLowerCase().includes(normalizedSearch) ||
        product.genre.toLowerCase().includes(normalizedSearch)

      const matchesGenre = genreFilter === 'All' || product.genre === genreFilter
      const matchesPrice = product.price <= maxPrice

      return matchesSearch && matchesGenre && matchesPrice
    })
  }, [activeVersion, genreFilter, maxPrice, search])

  const genres = useMemo(
    () => ['All', ...new Set(activeVersion.products.map((product) => product.genre))],
    [activeVersion],
  )

  const cartTotal = useMemo(
    () => Object.values(cart).reduce((sum, entry) => sum + entry.product.price * entry.quantity, 0),
    [cart],
  )

  const recordEvent = (eventType: string, payload: Record<string, unknown> = {}, targetSessionId = sessionId) => {
    if (!targetSessionId || isAgentSession) return
    enqueueResearchEvent(targetSessionId, { event_type: eventType, task_id: task, payload })
    void flushQueuedResearchEvents(targetSessionId)
  }

  const startHumanRun = async () => {
    if (sessionId) {
      setToast('End the active run before starting another session.')
      return
    }
    if (!consentGiven) {
      setToast('Confirm consent before starting a recorded session.')
      return
    }
    if (versions?.parity_check?.status !== 'passed') {
      setToast('A/B catalogue validation has not passed.')
      return
    }

    setRunStarting(true)
    try {
      const studyResponse = await fetch(`${API_BASE_URL}/api/studies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'BehaviourLens Mini Experiment',
          study_code: `DEMO-${crypto.randomUUID().slice(0, 8)}`,
          ethics_status: 'local_demo',
          preregistration_version: 'mini-v1',
        }),
      })
      if (!studyResponse.ok) throw new Error('Could not create study record.')
      const study = await studyResponse.json()

      const participantResponse = await fetch(`${API_BASE_URL}/api/studies/${study.id}/participants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recruitment_source: 'local_manual_demo',
          ui_language: 'en',
          assignment: { version: selectedVersion, persona: 'human_participant' },
        }),
      })
      if (!participantResponse.ok) throw new Error('Could not create participant record.')
      const participant = await participantResponse.json()

      const consentResponse = await fetch(`${API_BASE_URL}/api/participants/${participant.participant_id}/consent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ consent_status: 'consented' }),
      })
      if (!consentResponse.ok) throw new Error('Could not record consent.')

      const sessionResponse = await fetch(`${API_BASE_URL}/api/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          study_id: study.id,
          participant_id: participant.participant_id,
          ui_language: 'en',
          assigned_version: selectedVersion,
          task_instructions: TASK_INSTRUCTIONS[task],
        }),
      })
      if (!sessionResponse.ok) throw new Error((await sessionResponse.json()).detail ?? 'Could not start session.')
      const session = await sessionResponse.json()
      setSessionId(session.session_id)
      loadTaskState(task)
      enqueueResearchEvent(session.session_id, { event_type: 'session_started', task_id: task, payload: { actor_type: 'human', version: selectedVersion } })
      enqueueResearchEvent(session.session_id, { event_type: 'task_started', task_id: task, payload: { task_id: task } })
      void flushQueuedResearchEvents(session.session_id)
      setToast(`Recorded ${selectedVersion} ${task} session started.`)
    } catch (error) {
      setToast(error instanceof Error ? error.message : 'Could not start session.')
    } finally {
      setRunStarting(false)
    }
  }

  const verifyTask = async () => {
    const targetProductId = task === 'T1' ? 'book-2' : activeVersion.products[0]?.id
    const targetEntry = targetProductId ? cart[targetProductId] : undefined
    const success = task === 'T1'
      ? Boolean(targetEntry && targetEntry.quantity >= 1)
      : Boolean(targetEntry?.quantity === 2 && Object.keys(cart).length === 1 && cartTotal === targetEntry.product.price * 2)

    setTaskVerified(success)
    recordEvent(success ? 'task_completed' : 'task_failed', {
      success,
      cart: Object.values(cart).map(({ product, quantity }) => ({ product_id: product.id, quantity })),
      subtotal: Number(cartTotal.toFixed(2)),
    })
    setToast(success ? 'Final cart state verified. Task complete.' : 'The cart does not match the task outcome yet.')
    if (success && sessionId) {
      enqueueResearchEvent(sessionId, { event_type: 'session_completed', task_id: task, payload: { success: true } })
      await flushQueuedResearchEvents(sessionId)
      await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'completed' }),
      })
      await loadResults()
      setSessionId('')
    }
  }

  const endAndResetRun = async () => {
    if (!sessionId) return
    await flushQueuedResearchEvents(sessionId)
    await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'abandoned' }),
    })
    await loadResults()
    setSessionId('')
    loadTaskState(task)
    setToast('Run ended. Task state reset for a fresh session.')
  }

  const downloadResults = (format: 'json' | 'csv') => {
    const content = format === 'json'
      ? JSON.stringify(results, null, 2)
      : [
          ['session_id', 'actor_type', 'persona', 'model_name', 'version', 'task_id', 'status', 'success', 'duration_seconds', 'actions', 'retries', 'errors', 'failed_attempts'].join(','),
          ...results.map((result) => [
            result.session_id,
            result.actor_type,
            result.persona,
            result.model_name ?? '',
            result.version,
            result.task_id ?? '',
            result.status,
            result.success ?? '',
            result.duration_seconds ?? '',
            result.actions,
            result.retries,
            result.errors,
            result.failed_attempts,
          ].map((value) => `"${String(value).replaceAll('"', '""')}"`).join(',')),
        ].join('\n')
    const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `behaviourlens-results.${format}`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  const addToCart = (product: Product) => {
    recordEvent('product_viewed', { product_id: product.id })
    recordEvent('add_to_cart', {
      product_id: product.id,
      low_contrast: selectedVersion === 'A' && versionFlags.S7,
    })
    recordEvent('cart_updated', { product_id: product.id, action: 'add' })
    setCart((current) => {
      const existing = current[product.id]
      return {
        ...current,
        [product.id]: {
          product,
          quantity: existing ? existing.quantity + 1 : 1,
        },
      }
    })
    setToast(`${product.title} added to cart.`)
    setTimeout(() => setToast(''), 1500)
  }

  const updateQuantity = (productId: string, nextQuantity: number) => {
    if (nextQuantity <= 0) {
      recordEvent('quantity_changed', { product_id: productId, quantity: 0, removed: true })
      recordEvent('cart_updated', { product_id: productId, quantity: 0 })
      setCart((current) => {
        const updated = { ...current }
        delete updated[productId]
        return updated
      })
      return
    }

    if (selectedVersion === 'A' && (versions?.version_a?.feature_flags.S8 ?? false)) {
      setPendingQty((current) => ({ ...current, [productId]: nextQuantity }))
      recordEvent('quantity_changed', { product_id: productId, quantity: nextQuantity, requires_confirmation: true })
      setToast('Quantity updated after confirming the change.')
      return
    }

    recordEvent('quantity_changed', { product_id: productId, quantity: nextQuantity, requires_confirmation: false })
    recordEvent('cart_updated', { product_id: productId, quantity: nextQuantity })

    setCart((current) => {
      const entry = current[productId]
      if (!entry) return current
      return {
        ...current,
        [productId]: { ...entry, quantity: nextQuantity },
      }
    })
  }

  const applyPendingQty = (productId: string) => {
    const nextQty = pendingQty[productId]
    if (!nextQty) return

    recordEvent('cart_updated', { product_id: productId, quantity: nextQty, confirmed: true })

    setCart((current) => {
      const entry = current[productId]
      if (!entry) return current
      return {
        ...current,
        [productId]: { ...entry, quantity: nextQty },
      }
    })

    setPendingQty((current) => {
      const updated = { ...current }
      delete updated[productId]
      return updated
    })
    setToast('Quantity confirmed.')
    setTimeout(() => setToast(''), 1200)
  }

  const handleFormChange = (field: keyof FormValues, value: string) => {
    setForm((current) => ({ ...current, [field]: value }))
    setFormErrors((current) => ({ ...current, [field]: undefined }))
  }

  const handleCheckout = () => {
    recordEvent('checkout_started', {
      button_label: selectedVersion === 'A' && versionFlags.S10 ? 'Continue' : 'Proceed to checkout',
    })
    const errors: Partial<Record<keyof FormValues, string>> = {}

    if (!form.full_name.trim()) errors.full_name = 'Name is required.'
    if (!form.address.trim()) errors.address = 'Address is required.'
    if (!form.phone.trim()) errors.phone = 'Phone is required.'

    if (selectedVersion === 'A' && (versions?.version_a?.feature_flags.S3 ?? false)) {
      if (Object.keys(errors).length > 0) {
        recordEvent('validation_error', { fields: Object.keys(errors), message: 'Please correct the highlighted fields.' })
        setFormErrors({
          full_name: 'Please correct the highlighted fields.',
          phone: 'Please correct the highlighted fields.',
          address: 'Please correct the highlighted fields.',
        })
        setToast('Please correct the highlighted fields.')
        return
      }
    }

    if (Object.keys(errors).length > 0) {
      recordEvent('validation_error', { fields: Object.keys(errors) })
      setFormErrors(errors)
      setToast('Please fix the delivery details.')
      return
    }

    setFormErrors({})
    setToast('Delivery details confirmed. Research task complete.')
  }

  const versionFlags = activeVersion.feature_flags
  const startButtonLabel = runStarting ? 'Starting…' : sessionId ? 'Run active' : 'Start recorded run'

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Research platform</p>
          <h1>BehaviourLens</h1>
        </div>
        <div className="header-actions">
          <div className="status-pill">{health ? `${health.status.toUpperCase()} • ${health.app_name}` : 'Loading backend…'}</div>
          <div className="version-switcher">
            <button
              type="button"
              className={selectedVersion === 'A' ? 'active' : ''}
              disabled={Boolean(sessionId)}
              onClick={() => setSelectedVersion('A')}
            >
              Version A
            </button>
            <button
              type="button"
              className={selectedVersion === 'B' ? 'active' : ''}
              disabled={Boolean(sessionId)}
              onClick={() => setSelectedVersion('B')}
            >
              Version B
            </button>
          </div>
        </div>
      </header>

      <section className="overview-card">
        <div>
          <p className="section-label">Mini-experiment</p>
          <h2>Bookstore task session</h2>
          <p className="task-instruction">{TASK_INSTRUCTIONS[task]}</p>
        </div>
        <div className="run-controls">
          {isAgentSession ? <span className="session-indicator">AI agent session</span> : <>
          <label className="consent-check">
            <input type="checkbox" checked={consentGiven} onChange={(event) => setConsentGiven(event.target.checked)} />
            <span>I have read the local demo information and consent to recording this session.</span>
          </label>
          <p className="privacy-note">This local demonstration records interaction events only. Do not enter real names, phone numbers, or addresses.</p>
          <button type="button" className="start-run-button" onClick={() => void startHumanRun()} disabled={runStarting || Boolean(sessionId) || versions?.parity_check?.status !== 'passed'}>
            {startButtonLabel}
          </button>
          {sessionId ? <button type="button" className="end-run-button" onClick={() => void endAndResetRun()}>End run and reset</button> : null}
          <span className="session-indicator">{sessionId ? `Session ${sessionId}` : 'No active session'}</span>
          </>}
        </div>
      </section>

      <section className="workspace-panel">
        <aside className="control-panel">
          <div className="panel-section">
            <h3>Task states</h3>
            <div className="task-buttons">
              {TASKS.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={task === item ? 'task-button active' : 'task-button'}
                  disabled={!versions || Boolean(sessionId)}
                  onClick={() => loadTaskState(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div className="panel-section">
            <h3>Filter</h3>
            <label>
              Search
              <input
                aria-label="Search books by title or author"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    recordEvent('search_submitted', {
                      query_length: search.trim().length,
                      result_count: activeProducts.length,
                    })
                  }
                }}
                placeholder="Title or author"
              />
            </label>
            <label>
              {selectedVersion === 'A' && versionFlags.S1 ? 'Refine' : 'Filter by genre and price'}
              <select value={genreFilter} onChange={(event) => {
                setGenreFilter(event.target.value)
                recordEvent('filter_changed', {
                  filter: 'genre',
                  value: event.target.value,
                  filter_label: selectedVersion === 'A' && versionFlags.S1 ? 'Refine' : 'Filter by genre and price',
                })
              }}>
                {genres.map((genre) => (
                  <option key={genre} value={genre}>
                    {genre}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Max price
              <input type="range" min="10" max="25" value={maxPrice} onChange={(event) => {
                setMaxPrice(Number(event.target.value))
                recordEvent('filter_changed', { filter: 'max_price', value: Number(event.target.value) })
              }} />
              <span>{currency(maxPrice)}</span>
            </label>
          </div>

          <div className="panel-section">
            <h3>System cues</h3>
            <div className="flag-list">
              <span className={versionFlags.S1 ? 'flag active' : 'flag'}>S1 vague filter label</span>
              <span className={versionFlags.S3 ? 'flag active' : 'flag'}>S3 validation issues</span>
              <span className={versionFlags.S7 ? 'flag active' : 'flag'}>S7 contrast issue</span>
              <span className={versionFlags.S8 ? 'flag active' : 'flag'}>S8 hidden update step</span>
            </div>
          </div>
        </aside>

        <section className="catalog-panel">
          <div className="catalog-header">
            <div>
              <p className="catalog-label">Current task</p>
              <h3>{task}</h3>
            </div>
            <div className="filter-meta">{activeProducts.length} titles</div>
          </div>

          <div className="catalog-grid">
            {activeProducts.map((product) => (
              <article
                key={product.id}
                className="product-card"
                data-product-id={product.id}
                data-low-contrast={selectedVersion === 'A' && versionFlags.S7}
              >
                <div className="product-head">
                  <div>
                    <h4>{product.title}</h4>
                    <p>{product.author}</p>
                  </div>
                  <strong>{currency(product.price)}</strong>
                </div>

                <div className="product-meta">
                  <span>{product.genre}</span>
                  <span>⭐ {product.rating}</span>
                  <span>{product.reviews} reviews</span>
                </div>

                <p className="description">{product.description}</p>

                <div className="product-actions">
                  <button
                    type="button"
                    className={selectedVersion === 'A' && versionFlags.S7 ? 'purchase-button weak-contrast' : 'purchase-button'}
                    aria-label={`Add ${product.title} to cart`}
                    onClick={() => addToCart(product)}
                  >
                    Add to cart
                  </button>
                  {product.is_reviewed ? <span className="review-badge">Reviewed</span> : <span className="review-badge muted">Unreviewed</span>}
                </div>
              </article>
            ))}
          </div>
          {activeProducts.length === 0 ? <p className="empty-results">No books match these search and filter settings.</p> : null}
        </section>

        <aside className="cart-panel" data-testid="cart-panel">
          <div className="panel-section">
            <h3>Cart</h3>
            {Object.values(cart).length === 0 ? (
              <p className="empty-state">Your cart is empty.</p>
            ) : (
              <div className="cart-list">
                {Object.values(cart).map(({ product, quantity }) => (
                  <div key={product.id} className="cart-item" data-product-id={product.id} data-price={product.price}>
                    <div>
                      <strong>{product.title}</strong>
                      <p>{currency(product.price)} each</p>
                    </div>
                    <div className="cart-controls">
                      <button type="button" aria-label={`Decrease ${product.title} quantity`} onClick={() => updateQuantity(product.id, quantity - 1)}>-</button>
                      <span aria-label={`${product.title} quantity`} data-testid={`quantity-${product.id}`}>{pendingQty[product.id] ?? quantity}</span>
                      <button type="button" aria-label={`Increase ${product.title} quantity`} onClick={() => updateQuantity(product.id, quantity + 1)}>+</button>
                      {selectedVersion === 'A' && versionFlags.S8 && pendingQty[product.id] !== undefined && pendingQty[product.id] !== quantity ? (
                        <button type="button" className="confirm-btn" onClick={() => applyPendingQty(product.id)}>
                          Update
                        </button>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="cart-total">
              <span>Subtotal</span>
              <strong data-testid="cart-total">{currency(cartTotal)}</strong>
            </div>
            {!isAgentSession ? <>
              <button type="button" className="verify-task-button" onClick={verifyTask} disabled={!sessionId}>
                Verify final cart
              </button>
              {taskVerified ? <output className="verified-state">Task outcome verified from the cart.</output> : null}
            </> : null}
          </div>

          <div className="panel-section delivery-panel">
            <h3>Delivery details</h3>
            <label>
              Full name
              <input value={form.full_name} onChange={(event) => handleFormChange('full_name', event.target.value)} />
              {formErrors.full_name ? <span className="error-message">{formErrors.full_name}</span> : null}
            </label>
            <label>
              Phone
              <input value={form.phone} onChange={(event) => handleFormChange('phone', event.target.value)} />
              {formErrors.phone ? <span className="error-message">{formErrors.phone}</span> : null}
            </label>
            <label>
              Address
              <input value={form.address} onChange={(event) => handleFormChange('address', event.target.value)} />
              {formErrors.address ? <span className="error-message">{formErrors.address}</span> : null}
            </label>
            <label>
              Notes
              <textarea value={form.notes} onChange={(event) => handleFormChange('notes', event.target.value)} rows={3} />
            </label>
            <button type="button" className="checkout-button" onClick={handleCheckout}>
              {selectedVersion === 'A' && versionFlags.S10 ? 'Continue' : 'Proceed to checkout'}
            </button>
          </div>
        </aside>
      </section>

      {toast ? <div className="toast">{toast}</div> : null}

      <section className="parity-card">
        <h3>A/B parity check</h3>
        <div className="parity-grid">
          <span>Matched product count: {versions?.parity_check?.matched_product_count ?? 2}</span>
          <span>Same actions: {versions?.parity_check?.same_actions ? 'Yes' : 'No'}</span>
          <span>Same prices: {versions?.parity_check?.same_prices ? 'Yes' : 'No'}</span>
          <span>Same descriptions: {versions?.parity_check?.same_descriptions ? 'Yes' : 'No'}</span>
        </div>
        <p>{versions?.parity_check?.message ?? 'Parity validation pending.'}</p>
      </section>

      <section className="results-section">
        <div className="results-header">
          <div>
            <p className="section-label">Observed sessions</p>
            <h2>Mini-experiment results</h2>
          </div>
          <div className="results-actions">
            <button type="button" onClick={() => void loadResults()} aria-label="Refresh results">Refresh</button>
            <button type="button" onClick={() => downloadResults('csv')}>Export CSV</button>
            <button type="button" onClick={() => downloadResults('json')}>Export JSON</button>
          </div>
        </div>
        <div className="results-chart" aria-label="Browser actions by observed session">
          <h3>Browser actions per session</h3>
          {results.length === 0 ? <p>No recorded sessions yet.</p> : results.map((result) => {
            const maximumActions = Math.max(...results.map((item) => item.actions), 1)
            return (
              <div className="action-bar-row" key={result.session_id}>
                <span>{result.actor_type.toUpperCase()} · {result.persona} · {result.version}/{result.task_id ?? 'n/a'}</span>
                <div className="action-bar-track"><div className={result.actor_type === 'ai' ? 'action-bar ai' : 'action-bar human'} style={{ width: `${Math.max(4, result.actions / maximumActions * 100)}%` }} /></div>
                <strong>{result.actions}</strong>
              </div>
            )
          })}
        </div>
        <div className="results-table-wrap">
          <table className="results-table">
            <thead>
              <tr><th>Actor</th><th>Persona</th><th>Version</th><th>Task</th><th>Outcome</th><th>Duration</th><th>Actions</th><th>Retries</th><th>Errors</th><th>Failed attempts</th></tr>
            </thead>
            <tbody>
              {results.map((result) => (
                <tr key={result.session_id}>
                  <td>{result.actor_type}</td>
                  <td>{result.persona}</td>
                  <td>{result.version}</td>
                  <td>{result.task_id ?? 'n/a'}</td>
                  <td>{resultOutcomeLabel(result)}</td>
                  <td>{result.duration_seconds === null ? 'In progress' : `${result.duration_seconds}s`}</td>
                  <td>{result.actions}</td>
                  <td>{result.retries}</td>
                  <td>{result.errors}</td>
                  <td>{result.failed_attempts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  )
}

export default App
