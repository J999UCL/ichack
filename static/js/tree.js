/**
 * Tree Visualization JavaScript
 * Handles real-time tree updates via WebSocket with Gemini integration
 */

// Import Socket.IO from CDN
const io = window.io

class TreeVisualizer {
  constructor(articleData) {
    this.articleData = articleData
    this.articleTitle = articleData.title
    this.socket = null
    this.treeData = {}
    this.isSearching = false
    this.rateLimitTimer = null
    this.finalAnalysis = null

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

    console.log("✅ Socket.IO library is available")

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
        this.updateStatus("searching", `${data.ai_provider || "Gemini"} is finding related websites...`)
        // Clear any previous final analysis
        this.finalAnalysis = null
        this.renderTree()
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
          `Search complete! Found ${data.total_nodes || Object.keys(this.treeData).length} websites.`,
        )
      })

      // NEW: Handle final analysis
      this.socket.on("History Analysis Completed", (data) => {
        console.log("🧠 Final analysis received:", data)
        this.finalAnalysis = data.message
        this.renderTree() // Re-render to show the analysis
        this.updateStatus("connected", "Analysis complete! Check the insights above.")
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

    // Clear previous tree data and analysis
    this.treeData = {}
    this.finalAnalysis = null
    this.renderTree()

    // Emit start search event
    const searchData = {
      article_data: this.articleData,
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

    // Add final analysis section FIRST if available
    if (this.finalAnalysis) {
      const analysisSection = this.createAnalysisSection()
      treeContainer.appendChild(analysisSection)
    }

    // Then render tree
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
      if (this.finalAnalysis) {
        this.updateStatus("connected", "Gemini search and analysis complete!")
      } else {
        this.updateStatus("connected", "Gemini search complete!")
      }
    }
  }

  createAnalysisSection() {
    const section = document.createElement("div")
    section.className = "final-analysis-section"

    section.innerHTML = `
      <div class="final-analysis">
        <div class="final-analysis__header">
          <div class="final-analysis__icon">🧠</div>
          <h3 class="final-analysis__title">Gemini's Final Analysis</h3>
          <div class="final-analysis__badge">
            <span class="ai-badge ai-badge--small ai-badge--gemini">
              <span class="ai-badge__icon">✨</span>
              <span class="ai-badge__text">AI Insights</span>
            </span>
          </div>
        </div>
        <div class="final-analysis__content">
          <div class="final-analysis__text">${this.formatAnalysisText(this.finalAnalysis)}</div>
        </div>
        <div class="final-analysis__footer">
          <small class="final-analysis__note">
            This analysis was generated by Google Gemini based on all the articles discovered in your search tree below.
          </small>
        </div>
      </div>
    `

    return section
  }

  formatAnalysisText(text) {
    if (!text) return ""

    // Convert line breaks to HTML and escape HTML
    const escaped = this.escapeHtml(text)

    // Convert double line breaks to paragraphs
    const paragraphs = escaped.split("\n\n").filter((p) => p.trim())

    if (paragraphs.length > 1) {
      return paragraphs.map((p) => `<p>${p.replace(/\n/g, "<br>")}</p>`).join("")
    } else {
      // Single paragraph, just convert line breaks
      return `<p>${escaped.replace(/\n/g, "<br>")}</p>`
    }
  }

  showPlaceholder() {
    if (!this.treeVisualization) return

    this.treeVisualization.innerHTML = `
      <div class="tree-placeholder">
        <div class="tree-placeholder__icon">🌳</div>
        <h3 class="tree-placeholder__title">Ready to Explore: ${this.escapeHtml(this.articleTitle)}</h3>
        <p class="tree-placeholder__text">
          Click "Start Gemini Search" to watch as Google Gemini discovers related websites 
          and builds a knowledge tree of real articles, blogs, and resources in real-time.
        </p>
        <div class="tree-placeholder__info">
          <div class="info-box info-box--info">
            <span class="info-box__icon">✨</span>
            <div class="info-box__content">
              <strong>Powered by Google Gemini + Google Search</strong>
              <p>AI generates smart search queries, then finds real websites with articles, tutorials, and resources.</p>
            </div>
          </div>
        </div>
        <div class="tree-placeholder__features">
          <div class="feature">
            <span class="feature__icon">🔍</span>
            <span class="feature__text">Real websites</span>
          </div>
          <div class="feature">
            <span class="feature__icon">🔗</span>
            <span class="feature__text">Smart connections</span>
          </div>
          <div class="feature">
            <span class="feature__icon">🎯</span>
            <span class="feature__text">Relevant content</span>
          </div>
          <div class="feature">
            <span class="feature__icon">🧠</span>
            <span class="feature__text">AI analysis</span>
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

    // Create the main node content with website information
    const nodeTitle = this.escapeHtml(node.title)
    const nodeSource = node.source ? this.escapeHtml(node.source) : ""
    const nodeUrl = node.url || ""
    const nodeSnippet = node.snippet ? this.escapeHtml(node.snippet) : ""
    const searchQuery = node.search_query ? this.escapeHtml(node.search_query) : ""

    contentElement.innerHTML = `
      <div class="tree-node__header">
        <div class="tree-node__status-icon">${statusIcon}</div>
        <div class="tree-node__main">
          <div class="tree-node__title-row">
            <h4 class="tree-node__title">${nodeTitle}</h4>
            ${nodeSource ? `<span class="tree-node__source">${nodeSource}</span>` : ""}
          </div>
          ${nodeSnippet ? `<p class="tree-node__snippet">${nodeSnippet}</p>` : ""}
          ${searchQuery ? `<div class="tree-node__query">🔍 Found via: "${searchQuery}"</div>` : ""}
          ${
            nodeUrl
              ? `<div class="tree-node__url">
            <a href="${nodeUrl}" target="_blank" rel="noopener noreferrer" class="tree-node__link">
              🔗 Visit Website
            </a>
          </div>`
              : ""
          }
        </div>
        <div class="tree-node__timestamp">${this.formatTimestamp(node.timestamp)}</div>
      </div>
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
      hasFinalAnalysis: !!this.finalAnalysis,
    }
  }
}

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 DOM loaded, initializing TreeVisualizer...")

  // Get article data from the global variable set in the template
  const articleData = window.ARTICLE_DATA

  if (articleData && articleData.title) {
    console.log("📖 Article data from window.ARTICLE_DATA:", articleData)

    window.treeVisualizer = new TreeVisualizer(articleData)

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
    console.error("❌ Could not determine article data from window.ARTICLE_DATA")
  }
})
