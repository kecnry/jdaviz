<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Unit Conversion"
    v-model:api_hints_enabled="api_hints_enabled"
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#unit-conversion'"
    :disabled_msg="disabled_msg"
    :popout_button="popout_button"
    v-model:scroll_to="scroll_to">

    <plugin-select
      v-if="has_spectral"
      :items="spectral_unit_items.map(i => i.label)"
      v-model:selected="spectral_unit_selected"
      :show_if_single_entry="true"
      label="Spectral Unit"
      api_hint="plg.spectral_unit ="
      :api_hints_enabled="api_hints_enabled"
      hint="Global display unit for spectral axis."
    />

    <plugin-select
      v-if="has_time"
      :items="time_unit_items.map(i => i.label)"
      v-model:selected="time_unit_selected"
      :show_if_single_entry="true"
      label="Time Unit"
      api_hint="plg.time_unit ="
      :api_hints_enabled="api_hints_enabled"
      hint="Global display unit for time axis."
    />

    <plugin-select
      v-if="has_flux"
      :items="flux_unit_items.map(i => i.label)"
      v-model:selected="flux_unit_selected"
      :show_if_single_entry="true"
      label="Flux Unit"
      api_hint="plg.flux_unit ="
      :api_hints_enabled="api_hints_enabled"
      hint="Global display unit for flux axis."
    />

    <plugin-select
      v-if="has_angle"
      :items="angle_unit_items.map(i => i.label)"
      v-model:selected="angle_unit_selected"
      :show_if_single_entry="true"
      label="Angle Unit"
      api_hint="plg.angle_unit ="
      :api_hints_enabled="api_hints_enabled"
      hint="Global display unit for solid angle."
    />

    <j-flex-row v-if="has_sb">
      <v-text-field
        variant="underlined"
        v-model="sb_unit_selected"
        :label="api_hints_enabled ? 'plg.sb_unit' : 'Surface Brightness Unit'"
        :class="api_hints_enabled ? 'api-hint' : null"
        hint="Global display unit for surface brightness axis."
        persistent-hint
        :disabled='true'
      ></v-text-field>
    </j-flex-row>

    <div v-if="config == 'cubeviz' || config == 'deconfigged'">
      <j-flex-row>
        <v-divider></v-divider>
      </j-flex-row>

      <v-select
        :items="spectral_y_type_options"
        :model-value="spectral_y_type_selected"
        @update:model-value="spectral_y_type_selected = $event"
        label="Default and Synced Spectral y-axis Type"
        hint="Sets the quantity for new viewers and viewers synced to the app-wide setting."
        persistent-hint
      />

      <v-alert v-if="spectral_y_type_error" type="warning">
        {{ spectral_y_type_error }}
      </v-alert>


      <v-alert type="warning" v-if="!pixar_sr_exists">
            PIXAR_SR FITS header keyword not found when parsing spectral cube.
            Flux/Surface Brightness will use default PIXAR_SR value of 1.
      </v-alert>
    </div>

  </j-tray-plugin>
</template>
