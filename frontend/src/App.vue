<script setup>
import { onMounted, ref } from 'vue'

const API_URL = 'http://127.0.0.1:8000'

const hotelName = ref('')
const results = ref([])
const searchMessage = ref('')
const searchLoading = ref(false)

const users = ref([])
const selectedUserId = ref('')
const bookings = ref([])
const historyMessage = ref('')
const historyLoading = ref(false)

const actionMessage = ref('')

async function loadUsers() {
  try {
    const response = await fetch(`${API_URL}/api/users`)
    const data = await response.json()

    users.value = data.users

    if (users.value.length > 0) {
      selectedUserId.value = users.value[0].user_id
      await loadBookingHistory()
    }
  } catch (error) {
    console.error(error)
    actionMessage.value = 'Could not load demo travelers.'
  }
}

async function searchHotels() {
  const query = hotelName.value.trim()

  if (!query) {
    results.value = []
    searchMessage.value = 'Enter a hotel name.'
    return
  }

  searchLoading.value = true
  searchMessage.value = ''
  actionMessage.value = ''

  try {
    const response = await fetch(
      `${API_URL}/api/search?hotel_name=${encodeURIComponent(query)}`
    )

    if (!response.ok) {
      throw new Error('Search failed.')
    }

    const data = await response.json()
    results.value = data.results

    if (results.value.length === 0) {
      searchMessage.value = `No results found for "${query}".`
    }
  } catch (error) {
    console.error(error)
    searchMessage.value = 'Could not reach the backend.'
  } finally {
    searchLoading.value = false
  }
}

async function loadBookingHistory() {
  if (!selectedUserId.value) {
    bookings.value = []
    return
  }

  historyLoading.value = true
  historyMessage.value = ''

  try {
    const response = await fetch(
      `${API_URL}/api/bookings?user_id=${encodeURIComponent(selectedUserId.value)}`
    )

    if (!response.ok) {
      throw new Error('History request failed.')
    }

    const data = await response.json()
    bookings.value = data.bookings

    if (bookings.value.length === 0) {
      historyMessage.value = 'This traveler has no bookings.'
    }
  } catch (error) {
    console.error(error)
    historyMessage.value = 'Could not load booking history.'
  } finally {
    historyLoading.value = false
  }
}

async function bookTrip(trip) {
  if (!selectedUserId.value) {
    actionMessage.value = 'Choose a traveler before booking.'
    return
  }

  actionMessage.value = ''

  try {
    const response = await fetch(`${API_URL}/api/bookings`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: selectedUserId.value,
        trip_id: trip.trip_id,
      }),
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || 'Booking failed.')
    }

    actionMessage.value =
      `Booking ${data.booking_id} created successfully for ${trip.trip_name}.`

    await loadBookingHistory()
  } catch (error) {
    console.error(error)
    actionMessage.value = error.message
  }
}

async function cancelBooking(booking) {
  actionMessage.value = ''

  try {
    const response = await fetch(
      `${API_URL}/api/bookings/${booking.booking_id}/cancel`,
      {
        method: 'PATCH',
      }
    )

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || 'Cancellation failed.')
    }

    actionMessage.value =
      `Booking ${booking.booking_id} was cancelled and kept in history.`

    await loadBookingHistory()
  } catch (error) {
    console.error(error)
    actionMessage.value = error.message
  }
}

async function deleteBooking(booking) {
  actionMessage.value = ''

  try {
    const response = await fetch(
      `${API_URL}/api/bookings/${booking.booking_id}`,
      {
        method: 'DELETE',
      }
    )

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || 'Delete failed.')
    }

    actionMessage.value =
      `Booking ${booking.booking_id} was permanently deleted.`

    await loadBookingHistory()
  } catch (error) {
    console.error(error)
    actionMessage.value = error.message
  }
}

function formatRate(rate) {
  return Number(rate).toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
  })
}

onMounted(loadUsers)
</script>

<template>
  <main class="page">
    <header class="hero">
      <div>
        <p class="eyebrow">Travel booking demo</p>
        <h1>Expedia Lite</h1>
        <p class="subtitle">
          Search available hotel stays and manage simulated bookings.
        </p>
      </div>

      <div class="traveler-box">
        <label for="traveler">Demo traveler</label>

        <select
          id="traveler"
          v-model="selectedUserId"
          @change="loadBookingHistory"
        >
          <option
            v-for="user in users"
            :key="user.user_id"
            :value="user.user_id"
          >
            {{ user.display_name }} ({{ user.user_id }})
          </option>
        </select>
      </div>
    </header>

    <p v-if="actionMessage" class="notice">
      {{ actionMessage }}
    </p>

    <section class="panel">
      <div class="section-heading">
        <div>
          <h2>Find a stay</h2>
          <p>Search the available trips by hotel name.</p>
        </div>
      </div>

      <form class="search-row" @submit.prevent="searchHotels">
        <input
          v-model="hotelName"
          type="text"
          placeholder="Try Harbor Lantern Hotel"
          aria-label="Hotel name"
        />

        <button type="submit" :disabled="searchLoading">
          {{ searchLoading ? 'Searching...' : 'Search' }}
        </button>
      </form>

      <p v-if="searchMessage" class="message">
        {{ searchMessage }}
      </p>

      <div v-if="results.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Hotel</th>
              <th>Location</th>
              <th>Stay</th>
              <th>Dates</th>
              <th>Nightly rate</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="trip in results" :key="trip.trip_id">
              <td>
                <strong>{{ trip.hotel_name }}</strong>
                <span class="secondary">{{ trip.trip_id }}</span>
              </td>

              <td>{{ trip.city }}, {{ trip.state }}</td>

              <td>{{ trip.trip_name }}</td>

              <td>
                {{ trip.check_in }}
                <span class="secondary">to {{ trip.check_out }}</span>
              </td>

              <td>{{ formatRate(trip.nightly_rate_usd) }}</td>

              <td>
                <button
                  class="small-button"
                  type="button"
                  @click="bookTrip(trip)"
                >
                  Book
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <div class="section-heading">
        <div>
          <h2>Booking history</h2>
          <p>
            Create, review, cancel, and delete simulated reservations.
          </p>
        </div>

        <button
          class="secondary-button"
          type="button"
          @click="loadBookingHistory"
        >
          Refresh history
        </button>
      </div>

      <p v-if="historyLoading" class="message">
        Loading booking history...
      </p>

      <p v-else-if="historyMessage" class="message">
        {{ historyMessage }}
      </p>

      <div v-if="bookings.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Booking</th>
              <th>Hotel / Stay</th>
              <th>Dates</th>
              <th>Booked on</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="booking in bookings" :key="booking.booking_id">
              <td>
                <strong>{{ booking.booking_id }}</strong>
              </td>

              <td>
                {{ booking.hotel_name }}
                <span class="secondary">{{ booking.trip_name }}</span>
              </td>

              <td>
                {{ booking.check_in }}
                <span class="secondary">to {{ booking.check_out }}</span>
              </td>

              <td>{{ booking.booked_on }}</td>

              <td>
                <span
                  class="status"
                  :class="booking.status"
                >
                  {{ booking.status }}
                </span>
              </td>

              <td class="actions">
                <button
                  class="cancel-button"
                  type="button"
                  :disabled="booking.status === 'cancelled'"
                  @click="cancelBooking(booking)"
                >
                  Cancel
                </button>

                <button
                  class="delete-button"
                  type="button"
                  @click="deleteBooking(booking)"
                >
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>
</template>