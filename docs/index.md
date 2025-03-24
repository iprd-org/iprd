---
layout: default
title: IPRD - International Public Radio Directory
---

# International Public Radio Directory

Browse our collection of public radio streams from around the world.

{% raw %}
<div id="app">
  <div class="filters">
    <select v-model="selectedCountry">
      <option value="">All Countries</option>
      <option v-for="country in countries" :value="country">{{ country }}</option>
    </select>
    <input v-model="search" placeholder="Search stations...">
  </div>

  <table>
    <thead>
      <tr>
        <th>Station</th>
        <th>Country</th>
        <th>Language</th>
        <th>Stream</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="station in filteredStations">
        <td>{{ station.name }}</td>
        <td>{{ station.country }}</td>
        <td>{{ station.language }}</td>
        <td>
          <audio controls>
            <source :src="station.streams[0].url" :type="station.streams[0].format">
          </audio>
        </td>
      </tr>
    </tbody>
  </table>
</div>

<script src="https://cdn.jsdelivr.net/npm/vue@2"></script>
<script>
  fetch('/metadata/web-catalog.json')
    .then(response => response.json())
    .then(data => {
      new Vue({
        el: '#app',
        data: {
          stations: data.stations,
          selectedCountry: '',
          search: ''
        },
        computed: {
          countries() {
            return [...new Set(this.stations.map(s => s.country))].sort();
          },
          filteredStations() {
            return this.stations.filter(station => {
              const matchesCountry = !this.selectedCountry || station.country === this.selectedCountry;
              const matchesSearch = !this.search ||
                station.name.toLowerCase().includes(this.search.toLowerCase()) ||
                station.country.toLowerCase().includes(this.search.toLowerCase());
              return matchesCountry && matchesSearch;
            });
          }
        }
      });
    });
</script>
{% endraw %}
