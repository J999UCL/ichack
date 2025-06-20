/**
 * Tree Visualization JavaScript
 * Handles real-time tree updates via WebSocket with Gemini integration
 */

// Declare io variable before using it
let io

class TreeVisualizer {
  constructor(articleTitle) {
    this.articleTitle = articleTitle
    this.socket = null
    this.treeData = {}
    this.isSearching = false
    this.rateLimitTimer = null

    // Get DOM elements
    this.treeVisualization = document.getElementById("tree-visualization")
    this.statusIndicator = document.getElementById("status-indicator")
    this.startSearchBtn = document.getElementById("start-search")
    this.expandAllBtn = document.getElementById("expand-all")
    this.collapseAllBtn = document.getElementById("collapse-all")

    console.log("🚀 TreeVisualizer initialized for:", this.articleTitle)
    console.log("📊 DOM elements found:", {
      treeVisualization: !!this.treeVisualization,
      statusIndicator: !!this.statusIndicator,
      startSearchBtn: !!this.startSearchBtn,
      expandAllBtn: !!this.expandAllBtn,
      collapseAllBtn: !!this.collapseAllBtn,
    })

    this.init()
  }

  init() {
    this.initializeSocket()
    this.bindEvents()
    this.showPlaceholder()
  }

  initializeSocket() {
    console.log("🔌 Initializing Socket.IO connection...")

    // Check if io is available from the CDN
    if (typeof io === "undefined") {
      console.error("❌ Socket.IO not loaded! Check if the CDN script is working.")
      this.updateStatus("error", "Socket.IO library not available")
      return
    }

    try {
      // Initialize Socket.IO connection with proper configuration
      this.socket = io({
        transports: ["websocket", "polling"],
        timeout: 10000,
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 5,
        forceNew: false,
      })

      console.log("🔌 Socket.IO instance created:", this.socket)

      // Connection events
      this.socket.on("connect", () => {
        console.log("✅ Connected to server! Socket ID:", this.socket.id)
        this.updateStatus("connected", "Connected to server")

        // Enable the search button
        if (this.startSearchBtn) {
          this.startSearchBtn.disabled = false
        }
      })

      this.socket.on("disconnect", (reason) => {
        console.log("❌ Disconnected from server. Reason:", reason)
        this.updateStatus("error", `Disconnected: ${reason}`)

        // Disable the search button
        if (this.startSearchBtn) {
          this.startSearchBtn.disabled = true
        }
      })

      this.socket.on("connect_error", (error) => {
        console.error("❌ Connection error:", error)
        this.updateStatus("error", `Connection failed: ${error.message || error}`)
      })

      this.socket.on("reconnect", (attemptNumber) => {
        console.log("🔄 Reconnected after", attemptNumber, "attempts")
        this.updateStatus("connected", "Reconnected to server")
      })

      this.socket.on("reconnect_error", (error) => {
        console.error("❌ Reconnection error:", error)
        this.updateStatus("error", "Reconnection failed")
      })

      // Search events
      this.socket.on("search_started", (data) => {
        console.log("🔍 Search started:", data)
        this.updateStatus("searching", `${data.ai_provider || "Gemini"} is analyzing articles...`)
      })

      this.socket.on("tree_update", (treeData) => {
        console.log("📊 Tree update received:", treeData)
        this.treeData = treeData
        this.renderTree()
      })

      this.socket.on("search_complete", (data) => {
        console.log("✅ Search complete:", data)
        this.isSearching = false

        if (this.startSearchBtn) {
          this.startSearchBtn.disabled = false
          this.startSearchBtn.innerHTML = `
            <span class="btn__icon">✨</span>
            Start New Gemini Search
          `
        }

        this.updateStatus(
          "connected",
          `Search complete! Found ${data.total_nodes || Object.keys(this.treeData).length} articles.`,
        )
      })

      this.socket.on("rate_limit_warning", (data) => {
        console.log("⚠️ Rate limit warning:", data)
        this.handleRateLimit(data.message, data.wait_time)
      })

      this.socket.on("error", (error) => {
        console.error("❌ Socket error:", error)
        this.updateStatus("error", "Error: " + (error.message || error))
        this.isSearching = false

        if (this.startSearchBtn) {
          this.startSearchBtn.disabled = false
          this.startSearchBtn.innerHTML = `
            <span class="btn__icon">✨</span>
            Start Gemini Search
          `
        }
      })

      // Test events
      this.socket.on("connected", (data) => {
        console.log("📡 Server connection confirmed:", data)
      })

      this.socket.on("pong", (data) => {
        console.log("🏓 Pong received:", data)
      })

      // Initial connection attempt
      console.log("🔄 Attempting to connect...")
    } catch (error) {
      console.error("❌ Failed to initialize socket:", error)
      this.updateStatus("error", "Failed to initialize connection")
    }
  }

  bindEvents() {
    console.log("🔗 Binding event listeners...")

    if (this.startSearchBtn) {
      this.startSearchBtn.addEventListener("click", (e) => {
        e.preventDefault()
        console.log("🔍 Start search button clicked")
        this.startSearch()
      })
      console.log("✅ Start search button event bound")
    } else {
      console.error("❌ Start search button not found!")
    }

    if (this.expandAllBtn) {
      this.expandAllBtn.addEventListener("click", (e) => {
        e.preventDefault()
        this.expandAll()
      })
    }

    if (this.collapseAllBtn) {
      this.collapseAllBtn.addEventListener("click", (e) => {
        e.preventDefault()
        this.collapseAll()
      })
    }
  }

  startSearch() {
    console.log("🚀 Starting search process...")

    if (this.isSearching) {
      console.log("⚠️ Search already in progress")
      return
    }

    if (!this.socket) {
      console.error("❌ Socket not initialized")
      this.updateStatus("error", "Connection not initialized")
      return
    }

    if (!this.socket.connected) {
      console.error("❌ Socket not connected")
      this.updateStatus("error", "Not connected to server")

      // Try to reconnect
      console.log("🔄 Attempting to reconnect...")
      this.socket.connect()
      return
    }

    if (!this.articleTitle) {
      console.error("❌ No article title")
      this.updateStatus("error", "No article title specified")
      return
    }

    console.log("🔍 Starting search for:", this.articleTitle)

    // Update UI
    this.isSearching = true
    if (this.startSearchBtn) {
      this.startSearchBtn.disabled = true
      this.startSearchBtn.innerHTML = `
        <span class="btn__icon">⏳</span>
        Gemini is searching...
      `
    }

    this.updateStatus("searching", "Starting Gemini search...")

    // Clear previous tree data
    this.treeData = {}
    this.renderTree()

    // Emit start search event
    const searchData = {
      article_title: this.articleTitle,
    }

    console.log("📡 Emitting start_search event with data:", searchData)

    try {
      this.socket.emit("start_search", searchData)
      console.log("✅ Search request sent successfully")
    } catch (error) {
      console.error("❌ Failed to emit search request:", error)
      this.updateStatus("error", "Failed to send search request")
      this.isSearching = false
      if (this.startSearchBtn) {
        this.startSearchBtn.disabled = false
        this.startSearchBtn.innerHTML = `
          <span class="btn__icon">✨</span>
          Start Gemini Search
        `
      }
    }
  }

  handleRateLimit(message, waitTime) {
    console.log("⏳ Handling rate limit:", message, waitTime)

    this.updateStatus("warning", message)

    if (this.startSearchBtn) {
      this.startSearchBtn.disabled = true
    }

    // Clear any existing timer
    if (this.rateLimitTimer) {
      clearInterval(this.rateLimitTimer)
    }

    // Start countdown timer
    let remainingTime = Math.ceil(waitTime)

    const updateCountdown = () => {
      if (remainingTime <= 0) {
        clearInterval(this.rateLimitTimer)
        this.rateLimitTimer = null

        if (this.startSearchBtn) {
          this.startSearchBtn.disabled = false
          this.startSearchBtn.innerHTML = `
            <span class="btn__icon">✨</span>
            Start Gemini Search
          `
        }

        this.updateStatus("connected", "Ready to search")
        return
      }

      if (this.startSearchBtn) {
        this.startSearchBtn.innerHTML = `
          <span class="btn__icon">⏳</span>
          Wait ${remainingTime}s (Rate Limited)
        `
      }

      remainingTime--
    }

    // Update immediately and then every second
    updateCountdown()
    this.rateLimitTimer = setInterval(updateCountdown, 1000)
  }

  renderTree() {
    if (!this.treeVisualization) {
      console.error("❌ Tree visualization element not found")
      return
    }

    if (Object.keys(this.treeData).length === 0) {
      this.showPlaceholder()
      return
    }

    console.log("🌳 Rendering tree with", Object.keys(this.treeData).length, "nodes")

    // Find root node
    const rootNode = Object.values(this.treeData).find((node) => !node.parent_id)
    if (!rootNode) {
      console.log("❌ No root node found in tree data")
      return
    }

    console.log("🌱 Root node:", rootNode.title)

    // Clear visualization
    this.treeVisualization.innerHTML = ""

    // Create tree container
    const treeContainer = document.createElement("div")
    treeContainer.className = "tree-container-inner"

    // Render tree starting from root
    const treeElement = this.createTreeElement(rootNode, true)
    treeContainer.appendChild(treeElement)

    this.treeVisualization.appendChild(treeContainer)

    // Update search status
    if (this.isSearchComplete()) {
      this.isSearching = false
      if (this.startSearchBtn) {
        this.startSearchBtn.disabled = false
        this.startSearchBtn.innerHTML = `
          <span class="btn__icon">✨</span>
          Start New Gemini Search
        `
      }
      this.updateStatus("connected", "Gemini search complete!")
    }
  }

  showPlaceholder() {
    if (!this.treeVisualization) return

    this.treeVisualization.innerHTML = `
      <div class="tree-placeholder">
        <div class="tree-placeholder__icon">🌳</div>
        <h3 class="tree-placeholder__title">Ready to Explore: ${this.escapeHtml(this.articleTitle)}</h3>
        <p class="tree-placeholder__text">
          Click "Start Gemini Search" to watch as Google Gemini discovers and maps 
          related articles in real-time, building a knowledge tree before your eyes.
        </p>
        <div class="tree-placeholder__info">
          <div class="info-box info-box--info">
            <span class="info-box__icon">✨</span>
            <div class="info-box__content">
              <strong>Powered by Google Gemini</strong>
              <p>Advanced AI with faster responses and better understanding of complex topics.</p>
            </div>
          </div>
        </div>
        <div class="tree-placeholder__features">
          <div class="feature">
            <span class="feature__icon">⚡</span>
            <span class="feature__text">Fast discovery</span>
          </div>
          <div class="feature">
            <span class="feature__icon">🔗</span>
            <span class="feature__text">Smart connections</span>
          </div>
          <div class="feature">
            <span class="feature__icon">🎯</span>
            <span class="feature__text">Relevant topics</span>
          </div>
        </div>
      </div>
    `
  }

  createTreeElement(node, isRoot = false) {
    const nodeElement = document.createElement("div")
    nodeElement.className = `tree-node tree-node--${node.status}`
    if (isRoot) nodeElement.classList.add("tree-node--root")

    // Create node content
    const contentElement = document.createElement("div")
    contentElement.className = "tree-node__content"

    let statusIcon = ""
    switch (node.status) {
      case "searching":
        statusIcon = "🔍"
        break
      case "completed":
        statusIcon = "✅"
        break
      case "error":
        statusIcon = "❌"
        break
      case "rate_limited":
        statusIcon = "⏳"
        break
      default:
        statusIcon = "⚪"
    }

    contentElement.innerHTML = `
      <div class="tree-node__status"></div>
      <div class="tree-node__icon">${statusIcon}</div>
      <div class="tree-node__title">${this.escapeHtml(node.title)}</div>
      <div class="tree-node__timestamp">${this.formatTimestamp(node.timestamp)}</div>
    `

    // Add error message if present
    if (node.error_message) {
      const errorElement = document.createElement("div")
      errorElement.className = "tree-node__error"
      errorElement.textContent = node.error_message
      contentElement.appendChild(errorElement)
    }

    nodeElement.appendChild(contentElement)

    // Add children if they exist
    if (node.children && node.children.length > 0) {
      const childrenContainer = document.createElement("div")
      childrenContainer.className = "tree-children"

      node.children.forEach((childId) => {
        const childNode = this.treeData[childId]
        if (childNode) {
          const childElement = this.createTreeElement(childNode)
          childrenContainer.appendChild(childElement)
        }
      })

      nodeElement.appendChild(childrenContainer)
    }

    return nodeElement
  }

  updateStatus(type, message) {
    console.log(`📊 Status update: ${type} - ${message}`)

    if (this.statusIndicator) {
      this.statusIndicator.className = `status-indicator status-indicator--${type}`
      const textElement = this.statusIndicator.querySelector(".status-indicator__text")
      if (textElement) {
        textElement.textContent = message
      }
    }
  }

  isSearchComplete() {
    return Object.values(this.treeData).every(
      (node) => node.status === "completed" || node.status === "error" || node.status === "rate_limited",
    )
  }

  expandAll() {
    const childrenContainers = this.treeVisualization.querySelectorAll(".tree-children")
    childrenContainers.forEach((container) => {
      container.style.display = "block"
    })
    console.log("📖 Expanded all tree nodes")
  }

  collapseAll() {
    const childrenContainers = this.treeVisualization.querySelectorAll(".tree-children")
    childrenContainers.forEach((container) => {
      container.style.display = "none"
    })
    console.log("📕 Collapsed all tree nodes")
  }

  formatTimestamp(timestamp) {
    try {
      const date = new Date(timestamp)
      return date.toLocaleTimeString()
    } catch (error) {
      return "Unknown"
    }
  }

  escapeHtml(text) {
    const div = document.createElement("div")
    div.textContent = text || ""
    return div.innerHTML
  }

  // Public methods for debugging
  testConnection() {
    if (this.socket) {
      console.log("🧪 Testing socket connection...")
      this.socket.emit("test", { message: "Debug test from tree visualizer" })
    } else {
      console.error("❌ Socket not available")
    }
  }

  getStatus() {
    return {
      isSearching: this.isSearching,
      socketConnected: this.socket?.connected || false,
      treeDataCount: Object.keys(this.treeData).length,
      articleTitle: this.articleTitle,
      socketId: this.socket?.id,
    }
  }
}

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 DOM loaded, initializing TreeVisualizer...")

  // Get article title from the global variable set in the template
  let articleTitle = null

  // Declare ARTICLE_TITLE variable before using it
  const ARTICLE_TITLE = window.ARTICLE_TITLE

  if (typeof ARTICLE_TITLE !== "undefined" && ARTICLE_TITLE) {
    articleTitle = ARTICLE_TITLE
    console.log("📖 Article title from template:", articleTitle)
  } else {
    // Fallback: try to get from URL
    const pathParts = window.location.pathname.split("/")
    if (pathParts.length >= 3 && pathParts[1] === "tree") {
      articleTitle = decodeURIComponent(pathParts[2])
      console.log("🔄 Article title from URL:", articleTitle)
    }
  }

  if (articleTitle) {
    window.treeVisualizer = new TreeVisualizer(articleTitle)

    // Add debug functions to global scope
    window.debugTree = {
      testConnection: () => window.treeVisualizer.testConnection(),
      forceSearch: () => window.treeVisualizer.startSearch(),
      getStatus: () => window.treeVisualizer.getStatus(),
      reconnect: () => {
        if (window.treeVisualizer.socket) {
          window.treeVisualizer.socket.disconnect()
          window.treeVisualizer.socket.connect()
        }
      },
    }

    console.log("🔧 Debug functions available: window.debugTree")
  } else {
    console.error("❌ Could not determine article title")
  }
})
