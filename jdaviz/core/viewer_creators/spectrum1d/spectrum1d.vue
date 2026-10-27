<template>
  <j-viewer-creator
    :title="viewer_type"
    :popout_button="popout_button"
    :dataset_items="dataset_items"
    v-model:dataset_selected="dataset_selected"
    :dataset_multiselect="true"
    v-model:viewer_label_value="viewer_label_value"
    :viewer_label_default="viewer_label_default"
    v-model:viewer_label_auto="viewer_label_auto"
    :viewer_label_invalid_msg="viewer_label_invalid_msg"
    :api_hints_enabled="api_hints_enabled"
    @create-clicked="create_clicked"
  >
    <v-select
      v-model="spectral_y_type_selected"
      :items="[{title: 'App Default', value: ''},
               {title: 'Flux', value: 'Flux'},
               {title: 'Surface Brightness', value: 'Surface Brightness'}]"
      label="Spectral Quantity"
      hint="App Default follows the app setting. An explicit quantity disables synchronization for the new viewer."
      persistent-hint
    ></v-select>
  </j-viewer-creator>
</template>