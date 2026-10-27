
<script setup>
import { ref, computed, nextTick, onUnmounted } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const zipCode = ref('16802')
const loading = ref(false)
const errorMessage = ref('')
const mapError = ref('')
const location = ref(null)
const hotels = ref([])
const savedIds = ref(new Set())
const pendingIds = ref(new Set())
const feedback = ref('')
const resultSource = ref('')
const selectedHotelId = ref(null)
const mapElement = ref(null)

let map = null
let hotelMarkers = []

const selectedHotel = computed(() =>
  hotels.value.find(hotel => hotel.place_id === selectedHotelId.value)
)

function validCoordinates(latitude, longitude) {
  return (
    typeof latitude === 'number' &&
    typeof longitude === 'number' &&
    Number.isFinite(latitude) &&
    Number.isFinite(longitude) &&
    latitude >= -90 &&
    latitude <= 90 &&
    longitude >= -180 &&
    longitude <= 180
  )
}

function clearMap() {
  if (map) {
    map.remove()
    map = null
  }
  hotelMarkers = []
}

function hotelLabel(hotel) {
  return hotel.name || 'Name unavailable'
}

async function refreshSavedStatuses(items) {
  const statuses = await Promise.all(items.map(async hotel => {
    const response = await fetch(`/api/local/hotels/${encodeURIComponent(hotel.place_id)}/saved`)
    if (!response.ok) throw new Error('Could not check saved hotel status.')
    return [hotel.place_id, (await response.json()).saved]
  }))
  savedIds.value = new Set(statuses.filter(([, saved]) => saved).map(([id]) => id))
}

async function addLocal(hotel) {
  if (savedIds.value.has(hotel.place_id) || pendingIds.value.has(hotel.place_id)) return
  pendingIds.value = new Set([...pendingIds.value, hotel.place_id])
  feedback.value = ''
  try {
    const response = await fetch('/api/local/hotels', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hotel, postcode: location.value.postcode, location: location.value }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Could not save this hotel locally.')
    savedIds.value = new Set([...savedIds.value, hotel.place_id])
    feedback.value = `${hotelLabel(hotel)} saved locally.`
  } catch (error) {
    feedback.value = error.message || 'Could not save this hotel locally.'
  } finally {
    const next = new Set(pendingIds.value); next.delete(hotel.place_id); pendingIds.value = next
  }
}

async function removeLocal(hotel) {
  feedback.value = ''
  try {
    const response = await fetch(`/api/local/hotels/${encodeURIComponent(hotel.place_id)}`, { method: 'DELETE' })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Could not remove this hotel.')
    const next = new Set(savedIds.value); next.delete(hotel.place_id); savedIds.value = next
    if (resultSource.value === 'Saved locally') {
      hotels.value = hotels.value.filter(item => item.place_id !== hotel.place_id)
      if (selectedHotelId.value === hotel.place_id) selectedHotelId.value = hotels.value[0]?.place_id || null
      await nextTick()
      drawMap()
    }
    feedback.value = `${hotelLabel(hotel)} removed from local storage.`
  } catch (error) {
    feedback.value = error.message || 'Could not remove this hotel.'
  }
}

function distanceLabel(distance) {
  if (typeof distance !== 'number' || !Number.isFinite(distance)) {
    return 'Distance unavailable'
  }
  return `${(distance / 1000).toFixed(2)} km from ZIP center`
}

function hotelIcon(active) {
  return L.divIcon({
    className: active
      ? 'discovery-pin discovery-pin-selected'
      : 'discovery-pin',
    html: '<span aria-hidden="true">H</span>',
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  })
}

function selectHotel(placeId) {
  selectedHotelId.value = placeId

  for (const entry of hotelMarkers) {
    const selected = entry.hotel.place_id === placeId
    entry.marker.setIcon(hotelIcon(selected))

    if (selected && map) {
      map.panTo([
        entry.hotel.latitude,
        entry.hotel.longitude,
      ])
    }
  }

  // Make the selected row visible when a map marker was clicked.
  nextTick(() => {
    const row = Array.from(
      document.querySelectorAll('.discovery-hotel-button')
    ).find(button => button.dataset.placeId === placeId)

    row?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  })
}

function drawMap() {
  if (!mapElement.value || !location.value) return

  clearMap()

  const center = [
    location.value.latitude,
    location.value.longitude,
  ]

  map = L.map(mapElement.value).setView(center, 12)

  const tiles = L.tileLayer(
    'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }
  )

  tiles.on('tileerror', () => {
    mapError.value = 'Some map tiles could not be loaded.'
  })

  tiles.addTo(map)

  const radiusCircle = L.circle(center, {
    radius: 5000,
    color: '#2563eb',
    weight: 2,
    fillOpacity: 0.05,
  }).addTo(map)

  L.circleMarker(center, {
    radius: 5,
    color: '#1d4ed8',
    fillColor: '#1d4ed8',
    fillOpacity: 1,
  }).addTo(map).bindTooltip('Verified ZIP search center')

  for (const hotel of hotels.value) {
    const marker = L.marker(
      [hotel.latitude, hotel.longitude],
      {
        icon: hotelIcon(
          hotel.place_id === selectedHotelId.value
        ),
        title: hotelLabel(hotel),
        keyboard: true,
      }
    ).addTo(map)

    marker.on('click', () => {
      selectHotel(hotel.place_id)
    })

    hotelMarkers.push({ hotel, marker })
  }

  map.fitBounds(radiusCircle.getBounds(), {
    padding: [20, 20],
  })

  setTimeout(() => {
    map?.invalidateSize()
  }, 0)
}

async function findHotels() {
  if (loading.value) return

  const postcode = zipCode.value.trim()

  // Clear the previous search before starting a new one.
  clearMap()
  location.value = null
  hotels.value = []
  selectedHotelId.value = null
  errorMessage.value = ''
  mapError.value = ''
  feedback.value = ''
  resultSource.value = ''

  if (!/^[0-9]{5}$/.test(postcode)) {
    errorMessage.value = 'Enter exactly five digits for a U.S. ZIP code.'
    return
  }

  loading.value = true

  try {
    let response = await fetch(`/api/local/hotels?postcode=${encodeURIComponent(postcode)}`)
    let data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Could not check locally saved hotels.')
    if (data.count > 0) {
      location.value = data.location
      hotels.value = data.hotels
      resultSource.value = 'Saved locally'
      await refreshSavedStatuses(hotels.value)
    } else {
      response = await fetch(`/api/discovery/hotels?postcode=${encodeURIComponent(postcode)}`)
      data = await response.json()

    if (!response.ok) {
      throw new Error(
        typeof data.detail === 'string'
          ? data.detail
          : 'Hotel discovery request failed.'
      )
    }

    if (
      data.location?.postcode !== postcode ||
      data.location?.country_code?.toLowerCase() !== 'us' ||
      !validCoordinates(
        data.location?.latitude,
        data.location?.longitude
      ) ||
      data.radius_meters !== 5000 ||
      !Array.isArray(data.hotels)
    ) {
      throw new Error('The backend returned invalid location data.')
    }

    if (data.hotels.some(hotel =>
      !hotel ||
      typeof hotel.place_id !== 'string' ||
      !validCoordinates(hotel.latitude, hotel.longitude)
    )) {
      throw new Error('The backend returned invalid hotel coordinates.')
    }

    location.value = data.location
    hotels.value = data.hotels
    resultSource.value = 'API results'
    await refreshSavedStatuses(hotels.value)
    }

    if (hotels.value.length > 0) {
      selectedHotelId.value = hotels.value[0].place_id
    }

    await nextTick()

    try {
      drawMap()
    } catch (mapFailure) {
      console.error('Map could not initialize:', mapFailure)
      clearMap()
      mapError.value = 'The map could not be displayed.'
    }
    if (resultSource.value === 'Saved locally') {
      const nights = hotels.value.flatMap(hotel => hotel.nights || [])
      if (nights.length) feedback.value = 'Rates, availability, and dates shown are simulated classroom data.'
    }
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : 'Could not search for nearby hotels.'
  } finally {
    loading.value = false
  }
}

onUnmounted(clearMap)
</script>

<template>
  <section class="panel discovery-panel">
    <h2>Discover nearby hotels</h2>
    <p>
      Enter a five-digit U.S. ZIP code to find hotels within
      5 km of its verified location.
    </p>

    <form class="discovery-search" @submit.prevent="findHotels">
      <div>
        <label for="discovery-zip">U.S. ZIP code</label>
        <input
          id="discovery-zip"
          v-model="zipCode"
          type="text"
          inputmode="numeric"
          autocomplete="postal-code"
          placeholder="16802"
          aria-describedby="zip-instructions"
        />
        <small id="zip-instructions">
          Exactly five digits, including leading zeros.
        </small>
      </div>

      <button type="submit" :disabled="loading">
        {{ loading ? 'Finding hotels...' : 'Find Hotels' }}
      </button>
    </form>

    <p v-if="loading" role="status" class="discovery-message">
      Finding hotels near ZIP {{ zipCode }}...
    </p>

    <p v-if="errorMessage" role="alert" class="discovery-error">
      {{ errorMessage }}
    </p>
    <p v-if="feedback" role="status" class="discovery-message">{{ feedback }}</p>

    <template v-if="location">
      <p class="discovery-summary">
        <strong>ZIP {{ location.postcode }}</strong>
        <span v-if="location.locality">
          — {{ location.locality }}
        </span>
        · {{ resultSource === 'Saved locally' ? 'saved hotels associated with this ZIP' : `${hotels.length} hotel results within 5 km` }}
        · {{ resultSource }}
      </p>

      <p v-if="hotels.length === 0" role="status">
        No hotels were returned within 5 km of this ZIP location.
      </p>

      <div class="discovery-layout">
        <div class="discovery-list">
          <h3>Hotel results</h3>

          <div
            v-for="hotel in hotels"
            :key="hotel.place_id"
            type="button"
            class="discovery-hotel-button"
            :class="{
              'discovery-hotel-active':
                selectedHotelId === hotel.place_id
            }"
            :data-place-id="hotel.place_id"
            :aria-pressed="selectedHotelId === hotel.place_id"
            role="button"
            tabindex="0"
            @click="selectHotel(hotel.place_id)"
            @keydown.enter.prevent="selectHotel(hotel.place_id)"
            @keydown.space.prevent="selectHotel(hotel.place_id)"
          >
            <strong>{{ hotelLabel(hotel) }}</strong>
            <span>
              {{ hotel.address || 'Address unavailable' }}
            </span>
            <small>{{ distanceLabel(hotel.distance_meters) }}</small>
            <small v-if="hotel.nights?.length" class="simulated-data">Simulated classroom data</small>
            <ul v-if="hotel.nights?.length" class="hotel-nights">
              <li v-for="night in hotel.nights" :key="night.stay_date">
                {{ night.stay_date }}: ${{ (night.nightly_rate_cents / 100).toFixed(2) }}/night · {{ night.rooms_available }} rooms
              </li>
            </ul>
            <div class="local-actions" @click.stop>
              <button v-if="!savedIds.has(hotel.place_id)" type="button" :disabled="pendingIds.has(hotel.place_id)" @click="addLocal(hotel)">{{ pendingIds.has(hotel.place_id) ? 'Saving...' : 'Add to Local' }}</button>
              <button v-else type="button" @click="removeLocal(hotel)">Remove from Local</button>
              <small v-if="savedIds.has(hotel.place_id)">Saved locally</small>
            </div>
          </div>
        </div>

        <div class="discovery-map-column">
          <h3>Hotel map</h3>
          <div
            ref="mapElement"
            class="discovery-map"
            aria-label="Map of nearby hotels"
          ></div>

          <p v-if="mapError" role="alert" class="discovery-error">
            {{ mapError }}
          </p>

          <p v-if="selectedHotel" class="discovery-selected" role="status">
            Selected hotel:
            <strong>{{ hotelLabel(selectedHotel) }}</strong>
          </p>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.discovery-panel {
  margin-top: 24px;
}

.discovery-search {
  display: flex;
  align-items: end;
  gap: 14px;
  flex-wrap: wrap;
  margin: 20px 0;
}

.discovery-search > div {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.discovery-search input {
  padding: 11px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  width: 180px;
  font-size: 16px;
}

.discovery-search button {
  padding: 12px 20px;
  border: 0;
  border-radius: 8px;
  background: #1d4ed8;
  color: white;
  cursor: pointer;
}

.discovery-search button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.discovery-search small,
.discovery-hotel-button small {
  color: #64748b;
}

.discovery-message {
  margin: 12px 0;
}

.discovery-error {
  color: #b91c1c;
  margin: 12px 0;
}

.discovery-summary {
  margin: 18px 0;
}

.discovery-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.3fr);
  gap: 20px;
  margin-top: 20px;
}

.discovery-list {
  display: flex;
  flex-direction: column;
  gap: 9px;
  max-height: 520px;
  overflow-y: auto;
}

.discovery-hotel-button {
  text-align: left;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 6px;
  padding: 14px;
  background: white;
  color: #1e293b;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  cursor: pointer;
}

.local-actions { display: flex; align-items: center; gap: 10px; }
.local-actions button { width: fit-content; padding: 7px 10px; cursor: pointer; }
.hotel-nights { margin: 0; padding-left: 20px; font-size: 0.9rem; }
.simulated-data { font-weight: 600; }

.discovery-hotel-button:hover {
  background: #eff6ff;
}

.discovery-hotel-active {
  border: 2px solid #2563eb;
  background: #dbeafe;
}

.discovery-map {
  width: 100%;
  height: 450px;
  border-radius: 10px;
  overflow: hidden;
}

.discovery-selected {
  margin-top: 12px;
}

:deep(.discovery-pin) {
  background: #2563eb;
  color: white;
  border: 2px solid white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: bold;
  box-shadow: 0 1px 5px #475569;
}

:deep(.discovery-pin-selected) {
  background: #ea580c;
  border-color: #fff7ed;
  transform: scale(1.15);
}

@media (max-width: 780px) {
  .discovery-layout {
    grid-template-columns: 1fr;
  }

  .discovery-map {
    height: 350px;
  }
}
</style>
