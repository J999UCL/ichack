/**
 * Search functionality for Article Explorer
 * Handles Google Custom Search integration with improved UI state management
 */

class ArticleSearcher {
  constructor() {
    this.searchInput = document.getElementById("search-input")
    this.searchBtn = document.getElementById("search-btn")
    this.loadingContainer = document.getElementById("loading")
    this.resultsContainer = document.getElementById("results-container")
    this.resultsGrid = document.getElementById("results-grid")
    this.errorContainer = document.getElementById("error-container")
    this.errorMessage = document.getElementById("error-message")

    this.currentQuery = ""
    this.isSearching = false
    this.hasSearched = false

    this.init()
  }

  init() {
    this.bindEvents()
    this.focusSearchInput()
    this.checkApiStatus()
    this.resetUI()
  }

  resetUI() {
    // Ensure all sections are hidden initially
    this.hideAllSections()

    // Reset button state
    this.resetSearchButton()

    // Clear any previous results
    if (this.resultsGrid) {
      this.resultsGrid.innerHTML = ""
    }

    // Reset form state
    this.isSearching = false
    this.validateInput()
  }

  resetSearchButton() {
    if (this.searchBtn) {
      this.searchBtn.disabled = false
      this.searchBtn.innerHTML = `
        <span class="search-btn__icon">🔍</span>
        <span class="search-btn__text">Search</span>
      `
      this.searchBtn.classList.remove("btn--loading")
    }
  }

  async checkApiStatus() {
    try {
      const response = await fetch("/api/search-status")
      const status = await response.json()

      if (status.using_mock_data) {
        this.showApiNotice()
      }
    } catch (error) {
      console.log("Could not check API status:", error)
    }
  }

  showApiNotice() {
    // Check if notice already exists
    if (document.querySelector(".api-notice")) {
      return
    }

    // Create a notice banner
    const notice = document.createElement("div")
    notice.className = "api-notice"
    notice.innerHTML = `
      <div class="api-notice__content">
        <span class="api-notice__icon">ℹ️</span>
        <div class="api-notice__text">
          <strong>Demo Mode:</strong> Using realistic mock data. 
          <a href="#" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'; return false;">Configure real APIs</a>
          <div style="display:none; margin-top:0.5rem; font-size:0.9rem;">
            Set up <strong>Google Custom Search API</strong> and <strong>Gemini API</strong> in your .env file for real results.
            <br><small>Get API keys: <a href="https://developers.google.com/custom-search/v1/introduction" target="_blank">Google Search</a> | <a href="https://makersuite.google.com/app/apikey" target="_blank">Gemini</a></small>
          </div>
        </div>
        <button class="api-notice__close" onclick="this.parentElement.parentElement.remove()" title="Close">×</button>
      </div>
    `

    // Insert after header
    const header = document.querySelector(".header")
    if (header) {
      header.insertAdjacentElement("afterend", notice)
    }
  }

  bindEvents() {
    // Search button click
    if (this.searchBtn) {
      this.searchBtn.addEventListener("click", (e) => {
        e.preventDefault()
        this.performSearch()
      })
    }

    // Enter key in search input
    if (this.searchInput) {
      this.searchInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
          e.preventDefault()
          this.performSearch()
        }
      })

      // Input change for real-time validation
      this.searchInput.addEventListener("input", () => {
        this.validateInput()
      })

      // Focus and blur events
      this.searchInput.addEventListener("focus", () => {
        this.searchInput.parentElement.classList.add("search-input-container--focused")
      })

      this.searchInput.addEventListener("blur", () => {
        this.searchInput.parentElement.classList.remove("search-input-container--focused")
      })
    }

    // Suggestion tags
    const suggestionTags = document.querySelectorAll(".suggestion-tag")
    suggestionTags.forEach((tag) => {
      tag.addEventListener("click", (e) => {
        e.preventDefault()
        const query = tag.getAttribute("data-query")
        if (query) {
          this.searchInput.value = query
          this.performSearch()
        }
      })
    })

    // Handle browser back/forward
    window.addEventListener("popstate", () => {
      this.resetUI()
    })
  }

  validateInput() {
    const query = this.searchInput.value.trim()
    const isValid = query.length >= 2

    if (this.searchBtn) {
      this.searchBtn.disabled = !isValid || this.isSearching

      // Update button appearance based on state
      if (!isValid && !this.isSearching) {
        this.searchBtn.classList.add("btn--disabled")
      } else {
        this.searchBtn.classList.remove("btn--disabled")
      }
    }
  }

  focusSearchInput() {
    if (this.searchInput) {
      // Small delay to ensure page is fully loaded
      setTimeout(() => {
        this.searchInput.focus()
      }, 100)
    }
  }

  async performSearch() {
    const query = this.searchInput.value.trim()

    if (!query || query.length < 2) {
      this.showError("Please enter at least 2 characters to search")
      this.focusSearchInput()
      return
    }

    if (this.isSearching) {
      return
    }

    console.log("🔍 Performing search for:", query)

    this.currentQuery = query
    this.isSearching = true
    this.hasSearched = true
    this.showLoading()

    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: query,
          limit: 10,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || "Search failed")
      }

      if (data.success && data.results && data.results.length > 0) {
        this.showResults(data.results, query, data.using_mock_data)
      } else {
        this.showError("No articles found. Try a different search term.")
      }
    } catch (error) {
      console.error("Search error:", error)
      this.showError(error.message || "Search failed. Please try again.")
    } finally {
      this.isSearching = false
      this.validateInput()
    }
  }

  showLoading() {
    this.hideAllSections()

    if (this.loadingContainer) {
      this.loadingContainer.style.display = "block"
    }

    // Update search button
    if (this.searchBtn) {
      this.searchBtn.disabled = true
      this.searchBtn.classList.add("btn--loading")
      this.searchBtn.innerHTML = `
        <span class="search-btn__icon search-btn__spinner">⏳</span>
        <span class="search-btn__text">Searching...</span>
      `
    }

    // Update loading text with query
    const loadingText = this.loadingContainer?.querySelector(".loading__text")
    if (loadingText) {
      loadingText.textContent = `Searching for "${this.currentQuery}"...`
    }
  }

  showResults(results, query, usingMockData = false) {
    console.log("📊 Showing results:", results)

    this.hideAllSections()

    if (this.resultsContainer) {
      this.resultsContainer.style.display = "block"
    }

    // Update results title
    const resultsTitle = document.querySelector(".results__title")
    if (resultsTitle) {
      let titleText = `Search Results for "${query}"`
      if (usingMockData) {
        titleText += " (Demo Data)"
      }
      resultsTitle.textContent = titleText
    }

    // Update results description
    const resultsDescription = document.querySelector(".results__description")
    if (resultsDescription) {
      if (usingMockData) {
        resultsDescription.innerHTML = `
          <strong>Demo Mode:</strong> These are realistic mock results. 
          Configure Google Search API for real websites. 
          Click any result to see how Gemini explores connections.
        `
        resultsDescription.className = "results__description results__description--demo"
      } else {
        resultsDescription.innerHTML = `
          Click on any article to see how Google Gemini explores related topics and builds a knowledge tree in real-time.
        `
        resultsDescription.className = "results__description"
      }
    }

    // Render results
    this.renderResults(results)

    // Reset search button
    this.resetSearchButton()

    // Scroll to results
    this.scrollToResults()
  }

  renderResults(results) {
    if (!this.resultsGrid) return

    this.resultsGrid.innerHTML = ""

    results.forEach((result, index) => {
      const resultCard = this.createResultCard(result, index)
      this.resultsGrid.appendChild(resultCard)
    })
  }

  createResultCard(result, index) {
    const card = document.createElement("div")
    card.className = "result-card"
    card.setAttribute("data-index", index)

    // Add click handler
    card.addEventListener("click", (e) => {
      e.preventDefault()
      this.navigateToTree(result)
    })

    // Add keyboard support
    card.setAttribute("tabindex", "0")
    card.addEventListener("keypress", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault()
        this.navigateToTree(result)
      }
    })

    const imageUrl = result.image || "/static/images/placeholder.png"
    const snippet = result.snippet || "No description available"
    const source = result.source || "Unknown source"

    card.innerHTML = `
      <div class="result-card__image-container">
        <img 
          src="${this.escapeHtml(imageUrl)}" 
          alt="${this.escapeHtml(result.title)}"
          class="result-card__image"
          onerror="this.src='/static/images/placeholder.png'"
          loading="lazy"
        >
        <div class="result-card__source">${this.escapeHtml(source)}</div>
      </div>
      <div class="result-card__content">
        <h3 class="result-card__title">${this.escapeHtml(result.title)}</h3>
        <p class="result-card__snippet">${this.escapeHtml(snippet)}</p>
      </div>
      <div class="result-card__footer">
        <span class="result-card__action">Explore connections →</span>
      </div>
    `

    return card
  }

  navigateToTree(result) {
    console.log("🌳 Navigating to tree for:", result.title)

    // Show loading state on the clicked card
    const cards = document.querySelectorAll(".result-card")
    cards.forEach((card) => card.classList.remove("result-card--loading"))

    // Find the clicked card and add loading state
    const clickedCard = Array.from(cards).find(
      (card) => card.querySelector(".result-card__title").textContent === result.title,
    )
    if (clickedCard) {
      clickedCard.classList.add("result-card--loading")
    }

    // Encode the result data for the URL
    const encodedData = encodeURIComponent(
      JSON.stringify({
        title: result.title,
        url: result.url,
        snippet: result.snippet,
        image: result.image,
        source: result.source,
      }),
    )

    // Navigate to tree page
    window.location.href = `/tree?data=${encodedData}`
  }

  showError(message) {
    console.error("❌ Showing error:", message)

    this.hideAllSections()

    if (this.errorContainer) {
      this.errorContainer.style.display = "block"
    }

    if (this.errorMessage) {
      this.errorMessage.textContent = message
    }

    // Reset search button
    this.resetSearchButton()

    // Focus back on search input
    setTimeout(() => {
      this.focusSearchInput()
    }, 100)
  }

  hideAllSections() {
    const sections = [this.loadingContainer, this.resultsContainer, this.errorContainer]
    sections.forEach((section) => {
      if (section) {
        section.style.display = "none"
      }
    })
  }

  scrollToResults() {
    if (this.resultsContainer && this.hasSearched) {
      setTimeout(() => {
        this.resultsContainer.scrollIntoView({
          behavior: "smooth",
          block: "start",
        })
      }, 100)
    }
  }

  escapeHtml(text) {
    const div = document.createElement("div")
    div.textContent = text || ""
    return div.innerHTML
  }

  // Public methods for external use
  clearResults() {
    this.hideAllSections()
    if (this.resultsGrid) {
      this.resultsGrid.innerHTML = ""
    }
    this.hasSearched = false
  }

  getSearchState() {
    return {
      isSearching: this.isSearching,
      hasSearched: this.hasSearched,
      currentQuery: this.currentQuery,
    }
  }
}

// Global retry function
function retrySearch() {
  if (window.articleSearcher) {
    window.articleSearcher.performSearch()
  }
}

// Global clear function
function clearSearch() {
  if (window.articleSearcher) {
    window.articleSearcher.clearResults()
    window.articleSearcher.searchInput.value = ""
    window.articleSearcher.validateInput()
    window.articleSearcher.focusSearchInput()
  }
}

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 Initializing Article Searcher...")
  window.articleSearcher = new ArticleSearcher()
})

// Handle page visibility changes
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && window.articleSearcher) {
    // Page became visible again, validate UI state
    window.articleSearcher.validateInput()
  }
})
