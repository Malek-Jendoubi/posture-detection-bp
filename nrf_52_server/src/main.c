/*
 * Copyright (c) 2016 Intel Corporation
 *
 * SPDX-License-Identifier: Apache-2.0
 */

/*INCLUDES*/
#include "main.h"
#include "bmp5.h"
#include "bt-periph.h"

#define DEVICE_ID 3
#define SAMPLING_INTERVAL_MS 20
/* Declare the LED devices*/
#define LED_RED_NODE \
  DT_ALIAS(led0) // LED_RED_NODE = led0 defined in the .dts file


static const struct gpio_dt_spec led_red =
    GPIO_DT_SPEC_GET(LED_RED_NODE, gpios);

/* Sensor Data variables*/
struct bmp5_sensor_data sensor_data;
uint32_t pressure_data = 0;

/* BMP5 device variables*/
struct bmp5_dev dev;
struct bmp5_osr_odr_press_config osr_odr_press_cfg = {0};

int8_t bmp5_rslt;
int ret_led;

void new_packet();

/* Work queue callback for sample processing*/
static void sample_work_cb(struct k_work *work) {
  /*Get sensor data from the BMP581*/
  bmp5_rslt = get_sensor_data(&osr_odr_press_cfg, &dev);

  /* Make a new char array packet*/
  new_packet();

  /* Send the packet to the characteristic*/
  // printk("%s\n",frame_payload);
  sensor_notify(frame_payload);
}

K_WORK_DEFINE(sample_work, sample_work_cb);

/* Define timer_cb and timer*/
volatile uint64_t current_time_ms;

static void cts_timer_cb(struct k_timer *dummy) {
  current_time_ms++;
}
static void sample_timer_cb(struct k_timer *dummy) {
  k_work_submit(&sample_work);
}

K_TIMER_DEFINE(cts_timer, cts_timer_cb, NULL);
K_TIMER_DEFINE(sample_timer, sample_timer_cb, NULL);

#define _APP_TIMER_DEF (timer_id)

char frame_ts[10];
char frame_sensor[8];
static char frame_payload[SIZE_PAYLOAD];

void new_packet() {
  /* Frame : ID,XXXXXXXX,XXXXXX */
  sprintf(frame_payload, "%1d,%08lu,%06lu\n", DEVICE_ID,
          (unsigned long)current_time_ms, (unsigned long)sensor_data.pressure);

}

int main(void) {
  /* Initialize and check LED devices*/
  if (!gpio_is_ready_dt(&led_red)) {
    return 0;
  }

  ret_led = gpio_pin_configure_dt(&led_red, GPIO_OUTPUT_INACTIVE);
  if (ret_led < 0) {
    return 0;
  }

  bmp5_rslt = bmp5_interface_init(&dev, BMP5_I2C_INTF);
  if (bmp5_rslt == BMP5_OK) {
    bmp5_soft_reset(&dev);

    bmp5_rslt = bmp5_init(&dev);

    if (bmp5_rslt == BMP5_OK) {
      bmp5_rslt = set_config(&osr_odr_press_cfg, &dev);
    }
  }

  /* Initial sensor values*/
  get_sensor_data(&osr_odr_press_cfg, &dev);

  gpio_pin_set_dt(&led_red, 1);

  /* Start BLE stack and setup/run GATT Server*/
  bluetooth_advertiser_init();

  /*Start timers for Timestamping (1ms) and sample collection (SAMPLING_INTERVAL_MS) */
  k_timer_start(&cts_timer, K_MSEC(1), K_MSEC(1));
  k_timer_start(&sample_timer, K_MSEC(SAMPLING_INTERVAL_MS), K_MSEC(SAMPLING_INTERVAL_MS));

  while (1) {
    k_usleep(1);
      }

  return 0;
}

int8_t
get_sensor_data(const struct bmp5_osr_odr_press_config *osr_odr_press_cfg,
                struct bmp5_dev *dev) {
  int8_t rslt = 0;
  uint8_t int_status = 0x1;

  if (int_status & BMP5_INT_ASSERTED_DRDY) {
    /* pressure: sensor_data.pressure -- temperature: sensor_data.temperature */
    rslt = bmp5_get_sensor_data(&sensor_data, osr_odr_press_cfg, dev);
  }

  return rslt;
}
