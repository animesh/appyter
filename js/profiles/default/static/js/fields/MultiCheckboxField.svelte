<script>
  export let args
  let value = {}
  if (args.default) {
    for (const k of args.default) {
      value[k] = true
    }
  }
  $: args.value = JSON.stringify(Object.keys(value).filter(k => value[k]))
</script>

<style>
.cursor-pointer {
  cursor: pointer;
}
</style>

<div class="row px-3 pb-3">
  <div class="col-lg-3 bold text-lg-right my-auto">
    {args.label}
    {#if args.description}
      <sup><i class="far fa-question-circle" data-toggle="tooltip" title="" data-original-title={args.description}></i></sup>
    {/if}:
  </div>
  <div class="col-lg-6 pt-2 pt-lg-0">
    <ul class="list-group multi-checkbox-field">
      {#each args.choices as choice}
        <li
          class="list-group-item cursor-pointer"
          on:click={() => value[choice] = !value[choice]}
        >
          <div class="form-check">
            <input
              id="{args.name}-{choice}-checkbox"
              type="checkbox"
              class="form-check-input"
              bind:checked={value[choice]}
            />
            <label
              class="form-check-label"
              for="{args.name}-{choice}-checkbox"
            >{choice}</label>
          </div>
        </li>
      {/each}
    </ul>
    <input
      id={args.name}
      name={args.name}
      style="display: none;"
      type="text"
      value={args.value}
    />
  </div>
</div>
