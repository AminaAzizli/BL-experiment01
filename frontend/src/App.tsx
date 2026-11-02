import { useEffect, useMemo, useState } from 'react'
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

type ProductMap = Record<string, Product>

type Task = 'T1' | 'T2' | 'T3' | 'T4' | 'T5'

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

const TASKS: Task[] = ['T1', 'T2', 'T3', 'T4', 'T5']

const currency = (value: number) => `$${value.toFixed(2)}`

function App() {
  const [health, setHealth] = useState<{ status: string; app_name: string } | null>(null)
  const [versions, setVersions] = useState<{
    version_a?: VersionData
    version_b?: VersionData
    parity_check?: {
      matched_product_count: number
      same_actions: boolean
      same_prices: boolean
      same_descriptions: boolean
      message: string
    }
  } | null>(null)
  const [selectedVersion, setSelectedVersion] = useState<'A' | 'B'>('A')
  const [task, setTask] = useState<Task>('T1')
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

  useEffect(() => {
    const loadData = async () => {
      try {
        const healthResponse = await fetch('http://localhost:8000/api/health')
        if (healthResponse.ok) {
          setHealth(await healthResponse.json())
        }

        const bookstoreResponse = await fetch('http://localhost:8000/api/bookstore/versions')
        if (bookstoreResponse.ok) {
          const data = await bookstoreResponse.json()
          setVersions(data)
          loadTaskState('T1', data)
        }
      } catch (error) {
        console.error('Failed to load BehaviourLens data', error)
      }
    }

    void loadData()
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

  const loadTaskState = (nextTask: Task, data = versions) => {
    const productList = selectedVersion === 'A' ? (data?.version_a?.products ?? []) : (data?.version_b?.products ?? [])
    const lookup: ProductMap = Object.fromEntries(productList.map((product) => [product.id, product]))

    const seedCart: Record<string, CartEntry> = {}
    if (nextTask === 'T2' || nextTask === 'T3' || nextTask === 'T5') {
      const product = productList[0]
      if (product) {
        seedCart[product.id] = { product, quantity: 1 }
      }
    }
    if (nextTask === 'T5') {
      const second = productList[1]
      if (second) {
        seedCart[second.id] = { product: second, quantity: 2 }
      }
    }

    const formSeed: FormValues = {
      full_name: 'Fictional customer',
      phone: '555-0100',
      address: '123 Demo Street',
      notes: nextTask === 'T2' ? 'Gift wrap requested' : '',
    }

    setTask(nextTask)
    setCart(seedCart)
    setPendingQty({})
    setForm(formSeed)
    setFormErrors({})
    setToast(`Task ${nextTask} state loaded.`)
    setTimeout(() => setToast(''), 1600)

    if (nextTask === 'T4') {
      setSearch('signal')
    }
    if (nextTask === 'T5') {
      setSearch('')
    }

    // Keep an observable product context for the experiment shell.
    void lookup
  }

  const addToCart = (product: Product) => {
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
      setCart((current) => {
        const updated = { ...current }
        delete updated[productId]
        return updated
      })
      return
    }

    if (selectedVersion === 'A' && (versions?.version_a?.feature_flags.S8 ?? false)) {
      setPendingQty((current) => ({ ...current, [productId]: nextQuantity }))
      setToast('Quantity updated after confirming the change.')
      return
    }

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

    setCart((current) => {
      const entry = current[productId]
      if (!entry) return current
      return {
        ...current,
        [productId]: { ...entry, quantity: nextQty },
      }
    })

    setPendingQty((current) => ({ ...current, [productId]: 0 }))
    setToast('Quantity confirmed.')
    setTimeout(() => setToast(''), 1200)
  }

  const handleFormChange = (field: keyof FormValues, value: string) => {
    setForm((current) => ({ ...current, [field]: value }))
    setFormErrors((current) => ({ ...current, [field]: undefined }))
  }

  const handleCheckout = () => {
    const errors: Partial<Record<keyof FormValues, string>> = {}

    if (!form.full_name.trim()) errors.full_name = 'Name is required.'
    if (!form.address.trim()) errors.address = 'Address is required.'
    if (!form.phone.trim()) errors.phone = 'Phone is required.'

    if (selectedVersion === 'A' && (versions?.version_a?.feature_flags.S3 ?? false)) {
      if (Object.keys(errors).length > 0) {
        setFormErrors({
          full_name: errors.full_name ?? 'Please correct the highlighted fields.',
          phone: errors.phone ?? 'Please correct the highlighted fields.',
          address: errors.address ?? 'Please correct the highlighted fields.',
        })
        setToast('Validation message is unclear in this version.')
        return
      }
    }

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors)
      setToast('Please fix the delivery details.')
      return
    }

    setFormErrors({})
    setToast('Delivery details confirmed. Research task complete.')
  }

  const versionFlags = activeVersion.feature_flags

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
              onClick={() => setSelectedVersion('A')}
            >
              Version A
            </button>
            <button
              type="button"
              className={selectedVersion === 'B' ? 'active' : ''}
              onClick={() => setSelectedVersion('B')}
            >
              Version B
            </button>
          </div>
        </div>
      </header>

      <section className="overview-card">
        <div>
          <p className="section-label">Stage 2</p>
          <h2>Controlled bookstore and task-state shell</h2>
        </div>
        <ul>
          <li>Parallel product sets for Set 1 and Set 2.</li>
          <li>Feature flags for seeded UX issues in Version A.</li>
          <li>Search, filter, cart, quantity updates, and delivery validation.</li>
          <li>Preloaded task states for T1–T5.</li>
        </ul>
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
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Title or author" />
            </label>
            <label>
              {selectedVersion === 'A' && versionFlags.S1 ? 'Refine' : 'Filter by genre and price'}
              <select value={genreFilter} onChange={(event) => setGenreFilter(event.target.value)}>
                {genres.map((genre) => (
                  <option key={genre} value={genre}>
                    {genre}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Max price
              <input type="range" min="10" max="25" value={maxPrice} onChange={(event) => setMaxPrice(Number(event.target.value))} />
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
              <article key={product.id} className="product-card">
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
                    onClick={() => addToCart(product)}
                  >
                    Add to cart
                  </button>
                  {product.is_reviewed ? <span className="review-badge">Reviewed</span> : <span className="review-badge muted">Unreviewed</span>}
                </div>
              </article>
            ))}
          </div>
        </section>

        <aside className="cart-panel">
          <div className="panel-section">
            <h3>Cart</h3>
            {Object.values(cart).length === 0 ? (
              <p className="empty-state">Your cart is empty.</p>
            ) : (
              <div className="cart-list">
                {Object.values(cart).map(({ product, quantity }) => (
                  <div key={product.id} className="cart-item">
                    <div>
                      <strong>{product.title}</strong>
                      <p>{currency(product.price)} each</p>
                    </div>
                    <div className="cart-controls">
                      <button type="button" onClick={() => updateQuantity(product.id, quantity - 1)}>-</button>
                      <span>{pendingQty[product.id] ?? quantity}</span>
                      <button type="button" onClick={() => updateQuantity(product.id, quantity + 1)}>+</button>
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
              <strong>{currency(cartTotal)}</strong>
            </div>
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
              {selectedVersion === 'A' && versionFlags.S10 ? 'Continue to delivery details' : 'Proceed to checkout'}
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
    </main>
  )
}

export default App
