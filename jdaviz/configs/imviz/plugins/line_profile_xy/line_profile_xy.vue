<template>
  <j-tray-plugin
    description='Press l to plot line profiles across X and Y under cursor. You can also manually enter X and Y and the plot will update.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#line-profiles'"
    :popout_button="popout_button">

    <plugin-viewer-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      :multiselect="false"
      label="Viewer"
      :show_if_single_entry="false"
      hint="Select a viewer to plot."
    />

    <v-row no-gutters>
      <v-col>
        <v-text-field
          v-model='selected_x'
          type="number"
          label="X"
          hint="Value of X"
        ></v-text-field>
      </v-col>
    </v-row>

    <v-row no-gutters>
      <v-col>
        <v-text-field
          v-model='selected_y'
          type="number"
          label="Y"
          hint="Value of Y"
        ></v-text-field>
      </v-col>
    </v-row>

    <v-row v-if="plot_available">
      <!-- NOTE: the internal bqplot widget defaults to 480 pixels, so if choosing something else,
           we will likely need to override that with custom CSS rules in order to avoid the initial
           rendering of the plot from overlapping with content below -->
      <jupyter-widget :widget="line_plot_across_x" style="width: 100%; height: 480px" />
      <br/>
      <jupyter-widget :widget="line_plot_across_y" style="width: 100%; height: 480px" />
    </v-row>

  </j-tray-plugin>
</template>
