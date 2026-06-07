//============ Copyright (c) Valve Corporation, All rights reserved. ============
#pragma once

#include <atomic>
#include <memory>
#include <string>
#include <thread>

#include "openvr_driver.h"

struct MyHMDDisplayDriverConfiguration
{
	int32_t window_x;
	int32_t window_y;
	int32_t window_width;
	int32_t window_height;
	int32_t render_width;
	int32_t render_height;
};

class MyHMDDisplayComponent : public vr::IVRDisplayComponent
{
public:
	explicit MyHMDDisplayComponent( const MyHMDDisplayDriverConfiguration &config );

	bool IsDisplayOnDesktop() override;
	bool IsDisplayRealDisplay() override;
	void GetRecommendedRenderTargetSize( uint32_t *pnWidth, uint32_t *pnHeight ) override;
	void GetEyeOutputViewport( vr::EVREye eEye, uint32_t *pnX, uint32_t *pnY, uint32_t *pnWidth, uint32_t *pnHeight ) override;
	void GetProjectionRaw( vr::EVREye eEye, float *pfLeft, float *pfRight, float *pfTop, float *pfBottom ) override;
	vr::DistortionCoordinates_t ComputeDistortion( vr::EVREye eEye, float fU, float fV ) override;
	void GetWindowBounds( int32_t *pnX, int32_t *pnY, uint32_t *pnWidth, uint32_t *pnHeight ) override;
	bool ComputeInverseDistortion( vr::HmdVector2_t *pResult, vr::EVREye eEye, uint32_t unChannel, float fU, float fV ) override;

private:
	MyHMDDisplayDriverConfiguration config_;
};

class MyHMDDeviceDriver : public vr::ITrackedDeviceServerDriver
{
public:
	MyHMDDeviceDriver();

	vr::EVRInitError Activate( uint32_t unObjectId ) override;
	void EnterStandby() override;
	void *GetComponent( const char *pchComponentNameAndVersion ) override;
	void DebugRequest( const char *pchRequest, char *pchResponseBuffer, uint32_t unResponseBufferSize ) override;
	vr::DriverPose_t GetPose() override;
	void Deactivate() override;

	const std::string &MyGetSerialNumber();
	void MyRunFrame();
	void MyProcessEvent( const vr::VREvent_t &vrevent );
	void MyPoseUpdateThread();

private:
	void UpdateMouseLook();
	void KeyboardFilterThread();

	std::unique_ptr< MyHMDDisplayComponent > display_component_;
	std::string model_number_;
	std::string serial_number_;
	std::atomic< bool > is_active_{ false };
	std::atomic< uint32_t > device_index_{ vr::k_unTrackedDeviceIndexInvalid };
	std::atomic< float > yaw_{ 0.0f };
	std::atomic< float > pitch_{ 0.0f };
	std::atomic< float > pos_x_{ 0.0f };
	std::atomic< float > pos_z_{ 0.0f };
	std::atomic< float > height_offset_{ 0.0f };
	std::atomic< bool > mouse_capture_enabled_{ true };
	std::atomic< bool > f9_was_down_{ false };
	std::atomic< int > height_log_frame_{ 0 };
	std::atomic< bool > keyboard_filter_active_{ false };
	std::atomic< uint32_t > keyboard_filter_thread_id_{ 0 };
	std::thread pose_update_thread_;
	std::thread keyboard_filter_thread_;
};
