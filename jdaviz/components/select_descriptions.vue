<template>
  <v-select
    :menu-props="{ left: true }"
    attach
    :items="items"
    :v-model="selected"
    @change="$emit('update:selected', $event)"
    :label="label"
    :hint="hint"
    :rules="rules ? rules : []"
    :dense="dense"
    persistent-hint
  >
    <template v-slot:selection="{ item }">
      <span>
        {{ item.text }}
      </span>
    </template>
    <template v-slot:item="{ item }">
      <span>
        <b>
          {{ item.text }}
        </b>
        <span v-if="item.description" style="opacity: 0.85; font-size: 10pt">
          | {{ item.description }}
        </span>
      </span>
    </template>
 </v-select>
</template>

<script>
module.exports = {
  props: ['items', 'selected', 'label', 'hint', 'rules', 'dense']
};
</script>

<style scoped>
  .single-line {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
  }
</style>
