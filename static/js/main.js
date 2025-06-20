/**
 * Main JavaScript for Wikipedia Explorer
 * Handles article loading and navigation
 */

class WikipediaExplorer {
  constructor() {
    this.articlesContainer = document.getElementById("articles-container")
    this.articlesGrid = document.getElementById("articles-grid")
    this.loadingContainer = document.getElementById("loading")
    this.errorContainer = document.getElementById("error-container")
    this.errorMessage = document.getElementById("error-message")

    this.init()
  }

  init() {
    this.loadTrendingArticles()
  }

  async loadTrendingArticles() {
    try {
      this.showLoading()

      const response = await fetch("/api/trending")
      const data = await response.json()

      if (!data.success) {
        throw new Error(data.error || "Failed to load articles")
      }

      this.renderArticles(data.articles)
      this.showArticles()
    } catch (error) {
      console.error("Error loading articles:", error)
      this.showError(error.message)
    }
  }

  renderArticles(articles) {
    this.articlesGrid.innerHTML = ""

    articles.forEach((article) => {
      const articleCard = this.createArticleCard(article)
      this.articlesGrid.appendChild(articleCard)
    })
  }

  createArticleCard(article) {
    const card = document.createElement("div")
    card.className = "article-card"
    card.addEventListener("click", () => this.navigateToTree(article.title))

    const imageUrl = article.thumbnail || "/static/images/placeholder.png"
    const extract = article.extract || "No description available"

    card.innerHTML = `
            <img 
                src="${this.escapeHtml(imageUrl)}" 
                alt="${this.escapeHtml(article.title)}"
                class="article-card__image"
                onerror="this.src='/static/images/placeholder.png'"
            >
            <div class="article-card__content">
                <h3 class="article-card__title">${this.escapeHtml(article.title)}</h3>
                <p class="article-card__extract">${this.escapeHtml(extract)}</p>
            </div>
            <div class="article-card__footer">
                <span class="article-card__action">Explore connections →</span>
            </div>
        `

    return card
  }

  navigateToTree(articleTitle) {
    const encodedTitle = encodeURIComponent(articleTitle)
    window.location.href = `/tree/${encodedTitle}`
  }

  showLoading() {
    this.loadingContainer.style.display = "block"
    this.articlesContainer.style.display = "none"
    this.errorContainer.style.display = "none"
  }

  showArticles() {
    this.loadingContainer.style.display = "none"
    this.articlesContainer.style.display = "block"
    this.errorContainer.style.display = "none"
  }

  showError(message) {
    this.loadingContainer.style.display = "none"
    this.articlesContainer.style.display = "none"
    this.errorContainer.style.display = "block"
    this.errorMessage.textContent = message
  }

  escapeHtml(text) {
    const div = document.createElement("div")
    div.textContent = text
    return div.innerHTML
  }
}

// Initialize the application when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  new WikipediaExplorer()
})

// Global function for retry button
function loadTrendingArticles() {
  if (window.explorer) {
    window.explorer.loadTrendingArticles()
  }
}
