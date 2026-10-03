const skillPicker = document.getElementById("skillPicker");
const chosenSkills = document.getElementById("chosenSkills");
const selectedSkillIDs = document.getElementById("selectedSkillIDs");

if (skillPicker && chosenSkills && selectedSkillIDs) {
  skillPicker.removeAttribute("name");
  const selectedSkills = new Map();

  function renderChosenSkills() {
    chosenSkills.replaceChildren();
    selectedSkillIDs.replaceChildren();

    if (selectedSkills.size === 0) {
      const emptyMessage = document.createElement("span");
      emptyMessage.className = "chosen-skills-empty";
      emptyMessage.textContent = "No skills selected yet.";
      chosenSkills.append(emptyMessage);
    }

    for (const [skillID, skillName] of selectedSkills) {
      const chip = document.createElement("span");
      chip.className = "skill-chip";

      const name = document.createElement("span");
      name.textContent = skillName;

      const removeButton = document.createElement("button");
      removeButton.className = "skill-chip-remove";
      removeButton.type = "button";
      removeButton.setAttribute("aria-label", `Remove ${skillName}`);
      removeButton.textContent = "×";
      removeButton.addEventListener("click", () => {
        selectedSkills.delete(skillID);
        renderChosenSkills();
      });

      const hiddenInput = document.createElement("input");
      hiddenInput.type = "hidden";
      hiddenInput.name = "skillIDs";
      hiddenInput.value = skillID;
      selectedSkillIDs.append(hiddenInput);

      chip.append(name, removeButton);
      chosenSkills.append(chip);
    }

    for (const option of skillPicker.options) {
      if (option.value) {
        option.disabled = selectedSkills.has(option.value);
      }
    }
  }

  skillPicker.addEventListener("change", () => {
    const option = skillPicker.selectedOptions[0];
    if (!option || !option.value) {
      return;
    }

    selectedSkills.set(option.value, option.textContent.trim());
    skillPicker.value = "";
    renderChosenSkills();
  });
}
