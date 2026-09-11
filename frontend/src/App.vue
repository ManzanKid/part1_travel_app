<script setup>
import { ref } from 'vue'

const hotelName = ref('')
const results = ref([])
const message = ref('')
const loading = ref(false)

async function searchHotels() {
  const query = hotelName.value.trim()

  if (!query) {
    results.value = []
    message.value = 'Enter a hotel name.'
    return
  }

  loading.value = true
  message.value = ''
  results.value = []

  try {
    const response = await fetch(
      `http://localhost:8000/api/search?hotel_name=${encodeURIComponent(query)}`
    )

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`)
    }

    const data = await response.json()
    results.value = data.results

    if (data.results.length === 0) {
      message.value = `No results found for "${query}".`
    }
  } catch (error) {
    message.value = 'Could not reach the backend. Make sure FastAPI is running on port 8000.'
    console.error(error)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="container">
    <h1>Expedia Lite</h1>
    <p class="subtitle">Search hotel stays from the supplied CSV data.</p>

    <form class="search-row" @submit.prevent="searchHotels">
      <label for="hotel-search">Hotel name</label>
      <input
        id="hotel-search"
        v-model="hotelName"
        type="text"
        placeholder="e.g. Harbor Lantern Hotel"
      />
      <button type="submit" :disabled="loading">
        {{ loading ? 'Searching...' : 'Search' }}
      </button>
    </form>

    <p v-if="message" class="message">{{ message }}</p>

    <div v-if="results.length" class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Hotel</th>
            <th>City</th>
            <th>State</th>
            <th>Nightly Rate</th>
            <th>Trip ID</th>
            <th>Stay</th>
            <th>Check-in</th>
            <th>Check-out</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in results" :key="row.trip_id">
            <td>{{ row.hotel_name }}</td>
            <td>{{ row.city }}</td>
            <td>{{ row.state }}</td>
            <td>${{ row.nightly_rate_usd }}</td>
            <td>{{ row.trip_id }}</td>
            <td>{{ row.trip_name }}</td>
            <td>{{ row.check_in }}</td>
            <td>{{ row.check_out }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>
