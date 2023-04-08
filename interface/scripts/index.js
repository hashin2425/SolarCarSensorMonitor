dataset_list = {
  battery_v: {
    display_name: "バッテリー電圧",
    unit: "V",
    data: [],
    safe_range_min: -10000,
    safe_range_max: 10000,
    chart_obj: undefined,
  },
  battery_a: {
    display_name: "バッテリー残量",
    unit: "A",
    data: [],
    safe_range_min: 0,
    safe_range_max: 2,
    chart_obj: undefined,
  },
  battery_temp: {
    display_name: "バッテリー温度",
    unit: "℃",
    data: [],
    safe_range_min: -10000,
    safe_range_max: 10000,
    chart_obj: undefined,
  },
  body_temp: {
    display_name: "機体温度",
    unit: "℃",
    data: [],
    safe_range_min: -10000,
    safe_range_max: 10000,
    chart_obj: undefined,
  },
  speed: {
    display_name: "速度",
    unit: "km/h",
    data: [],
    safe_range_min: -10000,
    safe_range_max: 10000,
    chart_obj: undefined,
  },
  accelerator: {
    display_name: "アクセル",
    unit: "%",
    data: [],
    safe_range_min: -10000,
    safe_range_max: 10000,
    chart_obj: undefined,
  },
  break: {
    display_name: "ブレーキ",
    unit: "%",
    data: [],
    safe_range_min: -10000,
    safe_range_max: 10000,
    chart_obj: undefined,
  },
};

max_length_graph = 60;

document.addEventListener("DOMContentLoaded", function () {
  // Prevent page reload
  window.addEventListener("beforeunload", function (e) {
    e.preventDefault();
    e.returnValue = "本当に閉じますか？";
  });

  // Insert elements in container
  const containers = document.getElementById("graphs");
  const indicators = document.getElementById("indicators");
  Object.keys(dataset_list).forEach(function (id) {
    containers.innerHTML += `\
      <div class="container container_${id}">\
        <div class="labels">\
          <span class="name">${dataset_list[id].display_name}</span>\
          <span class="value value_${id}">1,234</span>\
          <span class="unit">${dataset_list[id].unit}</span>\
        </div>\
        <div class="chart">\
          <canvas id="chart_${id}"></canvas>\
        </div>\
      </div>\
      `;
    indicators.innerHTML += `\
      <div class="labels indicator indicator_${id}">\
        <span class="name">${dataset_list[id].display_name}</span>\
        <br>\
        <span class="value value_${id}">1,234</span>\
        <span class="unit">${dataset_list[id].unit}</span>\
      </div>\
      `;
  });

  // Enable each graphs
  Object.keys(dataset_list).forEach(function (id) {
    let this_canvas = document.getElementById(`chart_${id}`).getContext("2d");
    dataset_list[id].chart_obj = new Chart(this_canvas, {
      type: "line",
      data: {
        labels: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        datasets: [
          {
            label: "Value",
            data: dataset_list[id].data,
            borderWidth: 1,
            borderColor: "rgb(255, 99, 132)",
          },
        ],
      },
      options: {
        animation: {
          duration: 0,
        },
        responsive: true,
        plugins: {
          legend: {
            display: false,
          },
        },
        scales: {
          x: {
            min: 0,
            max: 100,
            display: true,
          },
          y: {
            display: true,
          },
        },
      },
    });
  });
});

// Receive data from python
eel.expose(Data_PY2JS);
function Data_PY2JS(data) {
  Object.keys(data).forEach(function (id) {
    if (Object.keys(dataset_list).includes(id)) {
      let new_data = data[id];
      dataset_list[id].data.push(new_data);
      dataset_list[id].chart_obj.data.labels.push("");

      if (dataset_list[id].data.length > max_length_graph) {
        dataset_list[id].data.shift();
        dataset_list[id].chart_obj.data.labels.shift();
      }
      dataset_list[id].chart_obj.update();

      Array.from(document.getElementsByClassName(`value_${id}`)).forEach((element) => {
        element.innerHTML = new_data;
      });

      Array.from(document.getElementsByClassName(`indicator_${id}`)).forEach((element) => {
        if (dataset_list[id].safe_range_max < new_data) {
          element.classList.add("danger");
          element.classList.remove("safe");
        } else if (dataset_list[id].safe_range_min > new_data) {
          element.classList.add("danger");
          element.classList.remove("safe");
        } else {
          element.classList.remove("danger");
          element.classList.add("safe");
        }
      });
    }
  });
}

function header_hide() {
  document.getElementById("header_on_hidden").style.display = "none";
  document.getElementById("header_on_shown").style.display = "flex";
}
function header_show() {
  document.getElementById("header_on_hidden").style.display = "flex";
  document.getElementById("header_on_shown").style.display = "none";
}
