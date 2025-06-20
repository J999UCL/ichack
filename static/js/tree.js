/**
 * Tree Visualization JavaScript
 * Handles real-time tree updates via WebSocket with Gemini integration
 */

// Import Socket.IO
const io = require("socket.io-client")

// Declare ARTICLE_TITLE variable
const ARTICLE_TITLE = "Default Article Title" // This should be replaced with the actual value or imported correctly

class TreeVisualizer {
  constructor(articleTitle) {
    this.articleTitle = articleTitle
    this.socket = null
    this.treeData = {}
    this.isSearching = false
    this.rateLimitTimer = null

    this.treeVisualization = document.getElementById("tree-visualization")
    this.statusIndicator = document.getElementById("status-indicator")
    this.startSearchBtn = document.getElementById("start-search")
    this.expandAllBtn = document.getElementById("expand-all")
    this.collapseAllBtn = document.getElementById("collapse-all")

    this.init()
  }

  init() {
    console.log("Initializing TreeVisualizer for:", this.articleTitle)
    this.initializeSocket()
    this.bindEvents()
    this.showPlaceholder()
  }

  initializeSocket() {
    console.log("Initializing Socket.IO connection...")

    // Initialize Socket.IO connection (io is loaded from CDN)
    this.socket = io()

    this.socket.on("connect", () => {
      console.log("✅ Connected to server")
      this.updateStatus("connected", "Connected to server")
    })

    this.socket.on("disconnect", () => {
      console.log("❌ Disconnected from server")
      this.updateStatus("error", "Disconnected from server")
    })

    this.socket.on("tree_update", (treeData) => {
      console.log("📊 Tree update received:", treeData)
      this.treeData = treeData
      this.renderTree()
    })

    this.socket.on("search_started", (data) => {
      console.log("🔍 Search started:", data)
      this.updateStatus("searching", `${data.ai_provider || "Gemini"} is analyzing articles...`)
    })

    this.socket.on("search_complete", (data) => {
      console.log("✅ Search complete:", data)
      this.isSearching = false
      this.startSearchBtn.disabled = false
      this.startSearchBtn.innerHTML = `
        <span class="btn__icon">✨</span>
        Start New Gemini Search
      `
      this.updateStatus("connected", `Search complete! Found ${data.total_nodes || 0} articles.`)
    })

    this.socket.on("rate_limit_warning", (data) => {
      console.log("⚠️ Rate limit warning:", data)
      this.handleRateLimit(data.message, data.wait_time)
    })

    this.socket.on("error", (error) => {
      console.error("❌ Socket error:", error)
      this.updateStatus("error", "Error: " + error.message)
      this.isSearching = false
      this.startSearchBtn.disabled = false
      this.startSearchBtn.innerHTML = `
        <span class="btn__icon">✨</span>
        Start Gemini Search
      `
    })

    this.socket.on("connect_error", (error) => {
      console.error("❌ Connection error:", error)
      this.updateStatus("error", "Connection failed - check server")
    })
  }

  bindEvents() {
    console.log("Binding event listeners...")

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
        console.log("📖 Expand all button clicked")
        this.expandAll()
      })
    }

    if (this.collapseAllBtn) {
      this.collapseAllBtn.addEventListener("click", (e) => {
        e.preventDefault()
        console.log("📕 Collapse all button clicked")
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

    if (!this.socket || !this.socket.connected) {
      console.error("❌ Socket not connected")
      this.updateStatus("error", "Not connected to server")
      return
    }

    console.log("🔍 Starting search for:", this.articleTitle)

    this.isSearching = true
    this.startSearchBtn.disabled = true
    this.startSearchBtn.innerHTML = `
      <span class="btn__icon">⏳</span>
      Gemini is searching...
    `
    this.updateStatus("searching", "Starting Gemini search...")

    // Clear previous tree data
    this.treeData = {}
    this.renderTree()

    // Emit start search event
    console.log("📡 Emitting start_search event...")
    this.socket.emit("start_search", {
      article_title: this.articleTitle,
    })

    console.log("✅ Search request sent")
  }

  handleRateLimit(message, waitTime) {
    console.log("⏳ Handling rate limit:", message, waitTime)

    this.updateStatus("warning", message)
    this.startSearchBtn.disabled = true

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
        this.startSearchBtn.disabled = false
        this.startSearchBtn.innerHTML = `
          <span class="btn__icon">✨</span>
          Start Gemini Search
        `
        this.updateStatus("connected", "Ready to search")
        return
      }

      this.startSearchBtn.innerHTML = `
        <span class="btn__icon">⏳</span>
        Wait ${remainingTime}s (Rate Limited)
      `

      remainingTime--
    }

    // Update immediately and then every second
    updateCountdown()
    this.rateLimitTimer = setInterval(updateCountdown, 1000)
  }

  renderTree() {
    if (Object.keys(this.treeData).length === 0) {
      this.showPlaceholder()
      return
    }

    console.log("🌳 Rendering tree with", Object.keys(this.treeData).length, "nodes")

    // Find root node
    const rootNode = Object.values(this.treeData).find((node) => !node.parent_id)
    if (!rootNode) {
      console.log("❌ No root node found")
      return
    }

    console.log("🌱 Root node:", rootNode.title)

    // Clear visualization
    this.treeVisualization.innerHTML = ""

    // Render tree starting from root
    const treeElement = this.createTreeElement(rootNode, true)
    this.treeVisualization.appendChild(treeElement)

    // Update search status
    if (this.isSearchComplete()) {
      this.isSearching = false
      this.startSearchBtn.disabled = false
      this.startSearchBtn.innerHTML = `
        <span class="btn__icon">✨</span>
        Start New Gemini Search
      `
      this.updateStatus("connected", "Gemini search complete!")
    }
  }

  showPlaceholder() {
    this.treeVisualization.innerHTML = `
      <div class="tree-placeholder">
        <div class="tree-placeholder__icon">🌳</div>
        <h3 class="tree-placeholder__title">Ready to Explore</h3>
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
    this.statusIndicator.className = `status-indicator status-indicator--${type}`
    this.statusIndicator.querySelector(".status-indicator__text").textContent = message
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
    const date = new Date(timestamp)
    return date.toLocaleTimeString()
  }

  escapeHtml(text) {
    const div = document.createElement("div")
    div.textContent = text
    return div.innerHTML
  }
}

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 DOM loaded, initializing TreeVisualizer...")

  // Get article title from the template variable
  if (typeof ARTICLE_TITLE !== "undefined" && ARTICLE_TITLE) {
    console.log("📖 Article title:", ARTICLE_TITLE)
    window.treeVisualizer = new TreeVisualizer(ARTICLE_TITLE)
  } else {
    console.error("❌ ARTICLE_TITLE not defined or empty")

    // Fallback: try to get from URL
    const pathParts = window.location.pathname.split("/")
    if (pathParts.length >= 3 && pathParts[1] === "tree") {
      const articleFromUrl = decodeURIComponent(pathParts[2])
      console.log("🔄 Using article title from URL:", articleFromUrl)
      window.treeVisualizer = new TreeVisualizer(articleFromUrl)
    } else {
      console.error("❌ Could not determine article title")
    }
  }
})

// Add some debugging functions to the global scope
window.debugTree = {
  testConnection: () => {
    if (window.treeVisualizer && window.treeVisualizer.socket) {
      console.log("🧪 Testing socket connection...")
      window.treeVisualizer.socket.emit("test", { message: "Debug test" })
    } else {
      console.error("❌ TreeVisualizer or socket not available")
    }
  },

  forceSearch: () => {
    if (window.treeVisualizer) {
      console.log("🧪 Forcing search start...")
      window.treeVisualizer.startSearch()
    } else {
      console.error("❌ TreeVisualizer not available")
    }
  },

  getStatus: () => {
    if (window.treeVisualizer) {
      return {
        isSearching: window.treeVisualizer.isSearching,
        socketConnected: window.treeVisualizer.socket?.connected,
        treeDataCount: Object.keys(window.treeVisualizer.treeData).length,
        articleTitle: window.treeVisualizer.articleTitle,
      }
    }
    return null
  },
}

console.log(
  "🔧 Debug functions available: window.debugTree.testConnection(), window.debugTree.forceSearch(), window.debugTree.getStatus()",
)
